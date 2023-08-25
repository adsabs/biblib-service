"""
Library view
"""
from biblib.views import USER_ID_KEYWORD
from biblib.utils import err, check_boolean
from biblib.models import User, Library, Permissions, Notes
from biblib.client import client
from biblib.views.base_view import BaseView
from flask import request, current_app
from flask_discoverer import advertise
from sqlalchemy import Boolean
from biblib.views.http_errors import MISSING_USERNAME_ERROR, SOLR_RESPONSE_MISMATCH_ERROR, \
    MISSING_LIBRARY_ERROR, NO_PERMISSION_ERROR, BAD_LIBRARY_ID_ERROR


class LibraryView(BaseView):
    """
    End point to interact with a specific library, only returns library content
    if the user has the correct privileges.

    The GET requests are separate from the POST, DELETE requests as this class
    must be scopeless, whereas the others will have scope.
    """
    decorators = [advertise('scopes', 'rate_limit')]
    scopes = []
    rate_limit = [1000, 60*60*24]

    @classmethod
    def get_documents_from_library(cls, library_id, service_uid):
        """
        Retrieve all the documents that are within the library specified
        :param library_id: the unique ID of the library
        :param service_uid: the user ID within this microservice

        :return: bibcodes
        """

        with current_app.session_scope() as session:
            # Get the library
            library = session.query(Library).filter_by(id=library_id).one()

            # Get the owner of the library
            result = session.query(Permissions, User)\
                .join(Permissions.user)\
                .filter(Permissions.library_id == library_id) \
                .filter(Permissions.permissions['owner'].astext.cast(Boolean).is_(True))\
                .one()
            owner_permissions, owner = result
            
            # Format service for later call
            service = '{api}/{uid}'.format(
                api=current_app.config['BIBLIB_USER_EMAIL_ADSWS_API_URL'],
                uid=owner.absolute_uid
            )
            current_app.logger.info('Obtaining email of user: {0} [API UID]'
                                    .format(owner.absolute_uid))

            response = client().get(
                service
            )

            # Get all the people who have permissions in this library
            users = session.query(Permissions).filter_by(
                library_id = library.id
            ).all()

            if response.status_code != 200:
                current_app.logger.error('Could not find user in the API'
                                         'database: {0}.'.format(service))
                owner = 'Not available'
            else:
                owner = response.json()['email'].split('@')[0]

            # User requesting to see the content
            main_permission = 'none'
            if service_uid:
                
                permission = session.query(Permissions).filter(
                    Permissions.user_id == service_uid
                ).filter(
                    Permissions.library_id == library_id
                ).one_or_none()

                if permission and permission.permissions['owner']:
                    main_permission = 'owner'
                elif permission and permission.permissions['admin']:
                    main_permission = 'admin'
                elif permission and permission.permissions['write']:
                    main_permission = 'write'
                elif permission and permission.permissions['read']:
                    main_permission = 'read'
                   

            if main_permission in ['owner', 'admin'] or library.public:
                num_users = len(users)
            else:
                num_users = 0

            metadata = dict(
                name=library.name,
                id='{0}'.format(cls.helper_uuid_to_slug(library.id)),
                description=library.description,
                num_documents=len(library.bibcode),
                date_created=library.date_created.isoformat(),
                date_last_modified=library.date_last_modified.isoformat(),
                permission=main_permission,
                public=library.public,
                num_users=num_users,
                owner=owner
            )
            session.refresh(library)
            session.expunge(library)

            return library, metadata

    @classmethod
    def read_access(cls, service_uid, library_id):
        """
        Defines which type of user has read permissions to a library.

        :param service_uid: the user ID within this microservice
        :param library_id: the unique ID of the library

        :return: boolean, access (True), no access (False)
        """

        read_allowed = ['read', 'write', 'admin', 'owner']
        for access_type in read_allowed:
            if cls.helper_access_allowed(service_uid=service_uid,
                                         library_id=library_id,
                                         access_type=access_type):
                return True

        return False

    @staticmethod
    def get_alternate_bibcodes(solr_docs):
        """
        Gets all the alternate bibcodes from solr docs 
        :param solr_docs: solr docs from the bigquery response
    

        :return: dict of alternate bibcodes and their corresponding canonical bibcodes {alternate_bibcode: canonical_bibcode}
        """
        alternate_bibcodes = {} 
        for doc in solr_docs:
            canonical_bibcode = doc['bibcode']
            if doc.get('alternate_bibcode'):
                alternate_bibcodes.update(
                    {alternate_bibcode: canonical_bibcode for alternate_bibcode in doc['alternate_bibcode']}
                )
        return alternate_bibcodes
    
    @staticmethod
    def update_notes(session, library, updated_list):
        """
        Updates the notes based on the solr canonical bibcodes response
        :param session: necessary for all the queries 
        :param library: library of the library to update
        :param updated_list: update_list: list of changed bibcodes {'before': 'after'}

        :return: updated_notes: list with all the notes that have been updated 
        """
        notes = session.query(Notes).filter(Notes.library_id == library.id).all() 
        updated_dict = {}

        for list_item in updated_list: 
            for key, value in list_item.items(): 
                updated_dict[key] = value
        
        updated_notes = []
        for note in notes: 
            if note.bibcode in updated_dict:  
                updated_notes.append(note)
                canonical_bibcode = updated_dict[note.bibcode]
                canonical_note = session.query(Notes).filter(Notes.library_id == library.id, 
                                                             Notes.bibcode == canonical_bibcode).one_or_none()
                if not canonical_note: 
                    new_note = Notes.create_unique(session=session, 
                                                content=note.content, 
                                                bibcode=canonical_bibcode, 
                                                library=note.library)
                    session.add(new_note)
                else: 
                    canonical_note.content = '{0} {1}'.format(canonical_note.content, note.content)
                
        session.commit()
        return updated_notes


    @staticmethod
    def solr_update_library(library_id, solr_docs):
        """
        Updates the library based on the solr canonical bibcodes response
        :param library: library_id of the library to update
        :param solr_docs: solr docs from the bigquery response

        :return: dictionary with details of files modified
                 num_updated: number of documents modified
                 duplicates_removed: number of files removed for duplication
                 update_list: list of changed bibcodes {'before': 'after'}
        """

        # Definitions
        new_library_bibcodes = {}

        # Output dictionary
        updates = dict(
                num_updated=0,
                duplicates_removed=0,
                update_list=[],
                updated_notes=[]
            )
        # Extract the canonical bibcodes and create a hashmap 
        # in which the alternate bibcode is the key and the canonical bibcode is the value
        alternate_bibcodes = LibraryView.get_alternate_bibcodes(solr_docs)

        with current_app.session_scope() as session:
            library = session.query(Library).filter(Library.id == library_id).one()
            for bibcode in library.bibcode:

                # Update if its an alternate
                if bibcode in alternate_bibcodes:
                    canonical = alternate_bibcodes[bibcode]
                    updates['num_updated'] += 1
                    updates['update_list'].append({bibcode: canonical})

                    # Only add the bibcode to the library if it is not there
                    if canonical not in new_library_bibcodes:
                        new_library_bibcodes[canonical] = library.bibcode[bibcode]
                    else:
                        updates['duplicates_removed'] += 1
                else:
                    new_library_bibcodes[bibcode] = library.bibcode[bibcode]

            if updates['update_list']:                
                LibraryView.update_database(session, library, new_library_bibcodes, updates)

            return updates
        
    @staticmethod
    def update_database(session, library, new_library_bibcodes, updates):
        """
        Carries the actual database update for the library and notes tables. 
        :param session: Necessary for the updates 
        :param library: Library to update
        :param new_library_bibcodes: The updated versions of all the bibcodes in the library
        :

        :return: dictionary with details of files modified
                 num_updated: number of documents modified
                 duplicates_removed: number of files removed for duplication
                 update_list: list of changed bibcodes {'before': 'after'}
        """

        library.bibcode = new_library_bibcodes
        session.add(library)
        session.commit()

        updates['updated_notes'] = LibraryView.update_notes(session, library, updates['update_list'])

    @staticmethod
    def load_parameters(request): 
        try:
            start = int(request.args.get('start', 0))
            max_rows = current_app.config.get('BIBLIB_MAX_ROWS', 100)
            max_rows *= float(
                request.headers.get('X-Adsws-Ratelimit-Level', 1.0)
            )
            max_rows = int(max_rows)
            rows = min(int(request.args.get('rows', 20)), max_rows)
            raw_library = check_boolean(request.args.get('raw', 'false'))

        except ValueError:
            current_app.logger.debug("Raised value error")
            start = 0
            rows = 20
            raw_library = False

        sort = request.args.get('sort', 'date desc')
        fl = request.args.get('fl', 'bibcode')
        current_app.logger.info('User gave pagination parameters:'
                                'start: {}, '
                                'rows: {}, '
                                'sort: "{}", '
                                'fl: "{}", '
                                'raw: "{}"'.format(start, rows, sort, fl, raw_library))
        return start, rows, sort, fl, raw_library
    
    def get_user_id_from_headers(self): 
        try:
            return int(request.headers[USER_ID_KEYWORD])
        except KeyError:
            current_app.logger.error('No username passed')
            return err(MISSING_USERNAME_ERROR)
    
    def get_library_from_slug(self, library):
        # Get library
        try:
            return self.helper_slug_to_uuid(library)
        except TypeError:
            return err(BAD_LIBRARY_ID_ERROR)
        
    def get_service_uid(self, user): 
        # If user exists, get their service uid 
        user_exists = self.helper_user_exists(absolute_uid=user)
        if user_exists:
            return self.helper_absolute_uid_to_service_uid(absolute_uid=user) 
        
    def process_library(self, user, service_uid, library_id, start, rows, sort, fl, raw_library):
        updates = {}
        documents = []
        # Try to load the dictionary and obtain the solr content
        library, metadata = self.get_documents_from_library(
            library_id=library_id,
            service_uid=service_uid
        )
        if raw_library: 
            solr = 'Only the raw library was requested.'
            current_app.logger.info('User: {0} requested only raw library output'
                                        .format(user))
        else: 
            solr, updates, documents = self._process_library_with_solr(library, start, rows, sort, fl)

        if not documents: 
            documents = library.get_bibcodes() 
            documents.sort() 
            documents = documents[start:start+rows] 

        response = {
            'documents': documents, 
            'solr': solr, 
            'metadata': metadata, 
            'updates': updates
        }
        return response
    
    def _process_library_with_solr(self, library, start, rows, sort, fl, updates, documents): 
        try:
            solr = self.solr_big_query(
                bibcodes=library.bibcode,
                start=start,
                rows=rows,
                sort=sort,
                fl=fl
            ).json()

            # Now check if we can update the library database based on the
            # returned canonical bibcodes
            if solr.get('response'):
                # Update bibcodes based on solrs response
                updates = self.solr_update_library(
                    library_id=library.id,
                    solr_docs=solr['response']['docs']
                )
                documents = [doc['bibcode'] for doc in solr['response']['docs']]
            else:
                # Some problem occurred, we will log it
                solr = SOLR_RESPONSE_MISMATCH_ERROR['body']
                current_app.logger.warning('Problem with solr response: {0}'
                                        .format(solr))
        except Exception as error:
            current_app.logger.warning('Could not parse solr data: {0}'
                                    .format(error))
            solr = {'error': 'Could not parse solr data'}
        return solr, updates, documents 
    

    def has_readonly_all_libraries_token(self):
        special_token = current_app.config.get('READONLY_ALL_LIBRARIES_TOKEN')
        return special_token and request.headers.get('Authorization', '').endswith(special_token)
    
    def has_read_access(self, service_uid, library):
        if not self.read_access(service_uid=service_uid,
                                library_id=library.id):
            current_app.logger.error(
                'User: {0} does not have access to library: {1}. DENIED'
                .format(service_uid, library.id)
            ) 
            return False 
        return True
    
    def handle_no_permission(self, user, library, no_service_uid): 
        if not no_service_uid: 
            current_app.logger.error('User:{0} does not exist in the database.'
                                        ' Therefore will not have extra '
                                        'privileges to view the library: {1}'
                                        .format(user, library.id))
        return err(NO_PERMISSION_ERROR)


    # Methods
    def get(self, library):
        """
        HTTP GET request that returns all the documents inside a given
        user's library
        :param library: library ID

        :return: list of the users libraries with the relevant information

        Header:
        -------
        Must contain the API forwarded user ID of the user accessing the end
        point

        Post body:
        ----------
        No post content accepted.

        Return data:
        -----------
        documents:    <list>   Currently, a list containing the bibcodes.
        solr:         <dict>   The response from the solr bigquery end point
        metadata:     <dict>   contains the following:

          name:                 <string>  Name of the library
          id:                   <string>  ID of the library
          description:          <string>  Description of the library
          num_documents:        <int>     Number of documents in the library
          date_created:         <string>  ISO date library was created
          date_last_modified:   <string>  ISO date library was last modified
          permission:           <sting>   Permission type, can be: 'read',
                                          'write', 'admin', or 'owner'
          public:               <boolean> True means it is public
          num_users:            <int>     Number of users with permissions to
                                          this library
          owner:                <string>  Identifier of the user who created
                                          the library

        updates:      <dict>   contains the following

          num_updated:          <int>     Number of documents modified based on
                                          the response from solr
          duplicates_removed:   <int>     Number of files removed because
                                          they are duplications
          update_list:          <list>[<dict>]
                                          List of dictionaries such that a
                                          single element described the original
                                          bibcode (key) and the updated bibcode
                                          now being stored (item)

          updated_notes:        <list>    List of all the notes that have been updated 


        Permissions:
        -----------
        The following type of user can read a library:
          - owner
          - admin
          - write
          - read

        Default Pagination Values:
        -----------
        - start: 0
        - rows: 20 (max 100)
        - sort: 'date desc'
        - fl: 'bibcode'

        """
        
        user = self.get_user_id_from_headers()
        # Parameters to be forwarded to Solr: pagination, and fields
        start, rows, sort, fl, raw_library = LibraryView.load_parameters(request)
        library = self.get_library_from_slug(library)
        current_app.logger.info('User: {0} requested library: {1}'
                                .format(user, library))
        
        service_uid = self.get_service_uid(user)

        if not service_uid or not self.has_read_access(service_uid, library_id=library.id):
            # no_service_uid is going to be True if service_uid is False
            no_service_uid = not service_uid 
            return self.handle_no_permission(user, library, no_service_uid) 
        
        try: 
            response = self.process_library(user, service_uid, library, start, rows, sort, fl, raw_library)
        except Exception as error: 
            current_app.logger.warning(
                'Library missing or solr endpoint failed: {0}'
                .format(error)
            )
            return err(MISSING_LIBRARY_ERROR)

    
        if library.public or self.has_readonly_all_libraries_token():
            current_app.logger.info('Library: {0} is public'
                                    .format(library.id))
        else:
            current_app.logger.warning('Library: {0} is private'
                                       .format(library.id)) 

        # If they have access, let them obtain the requested content
        current_app.logger.info('User: {0} has access to library: {1}. '
                                'ALLOWED'
                                .format(user, library.id))

        return response, 200
