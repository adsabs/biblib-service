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
    def get_documents_from_library(cls, library_id, service_uid, session):
        """
        Retrieve all the documents that are within the library specified
        :param library_id: the unique ID of the library
        :param service_uid: the user ID within this microservice

        :return: bibcodes
        """

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
    
    @classmethod
    def get_alternate_bibcodes(cls, solr_docs):
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
    
    @classmethod
    def update_notes(cls, session, library, updated_list):
        """
        Updates the notes based on the solr canonical bibcodes response
        :param session: necessary for all the queries 
        :param library: library to update
        :param updated_list: list of changed bibcodes {'before': 'after'}

        :return: updated_notes: list with all the notes that have been updated 
        """
        notes = session.query(Notes).filter(Notes.library_id == library.id).all() 
        updated_dict = {}
        
        # Turn list into a dictionary for fast lookup
        for updated_bibcode in updated_list: 
            for key, value in updated_bibcode.items(): 
                updated_dict[key] = value
        
        updated_notes = []
        for note in notes: 
            if note.bibcode in updated_dict:  
                updated_notes.append(note)
                canonical_bibcode = updated_dict[note.bibcode]
                canonical_note = session.query(Notes).filter(Notes.library_id == library.id, 
                                                             Notes.bibcode == canonical_bibcode).one_or_none()
                # If there's no note with the canonical bibcode, create a new note
                if not canonical_note: 
                    new_note = Notes.create_unique(session=session, 
                                                content=note.content, 
                                                bibcode=canonical_bibcode, 
                                                library=note.library)
                    session.add(new_note)
                # If there's already a note, merge the contents
                else: 
                    canonical_note.content = '{0} {1}'.format(canonical_note.content, note.content)
                
        session.commit()
        return updated_notes

    @classmethod
    def update_database(cls, session, library, new_library_bibcodes, updates):
        """
        Carries the actual database update for the library and notes tables. 
        :param session: Necessary for the updates 
        :param library: Library to update
        :param new_library_bibcodes: The updated versions of all the bibcodes in the library
        :param updates: dictionary with all the updates

        :return: updates dictionary with details of files modified. They keys in the dictionary are:
                 num_updated: number of documents modified
                 duplicates_removed: number of files removed for duplication
                 update_list: list of changed bibcodes {'before': 'after'}
                 updated_notes: list of notes that were updates
        """
        library.bibcode = new_library_bibcodes
        session.add(library)
        session.commit()

        updates['updated_notes'] = cls.update_notes(session, library, updates['update_list'])


    @classmethod
    def solr_update_library(cls, library_id, solr_docs):
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
        alternate_bibcodes = cls.get_alternate_bibcodes(solr_docs)

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
                cls.update_database(session, library, new_library_bibcodes, updates)

            return updates
        
    def get_user_id_from_headers(self, request): 
        """
        Gets the user id from the request headers
        :param request: request object

        :return: user_id if it exists and None otherwise
                 Error message if the user does not exist and None otherwise
                 
        """
        try:
            user = int(request.headers[USER_ID_KEYWORD])
            return user, None
        except KeyError:
            current_app.logger.error('No username passed')
            return None, err(MISSING_USERNAME_ERROR)
        
    def load_parameters(self, request): 
        """
        Loads parameters necessary for the Solr search
        :param request: request object

        :return: start: int representing the start of the pagination
                 rows: int representing the number of rows to be returned
                 sort: enum representing the sort order 
                 fl: str representing the field to be returned
                 raw_library: boolean 
      
        """
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
    
    def get_library_from_slug(self, user, library):
        """
        Retrieves library id from slug
        :param user: user_id
        :param library: library slug

        :return: library_id: if it exists and None otherwise
                 BAD_LIBRARY_ID_ERROR: if the library is not found 
      
        """
        try:
            library = self.helper_slug_to_uuid(library)
            current_app.logger.info('User: {0} requested library: {1}'
                                .format(user, library))
            return library, None
        except TypeError:
            return None, err(BAD_LIBRARY_ID_ERROR)
        
    def get_service_uid(self, user): 
        """
        Retrieves the user id for service 
        :param user: user
        

        :return: uid: if it exists and None otherwise
        """
        # If user exists, get their service uid 
        user_exists = self.helper_user_exists(absolute_uid=user)
        if user_exists:
            return self.helper_absolute_uid_to_service_uid(absolute_uid=user) 
        
    def has_read_access(self, service_uid, library):
        """
        Checks if the user has read access 
        :param service_uid: user service id 
        :param library: 
        

        :return: uid: if it exists and None otherwise
        """
        if not self.read_access(service_uid=service_uid,
                                library_id=library.id):
            current_app.logger.error(
                'User: {0} does not have access to library: {1}. DENIED'
                .format(service_uid, library.id)
            ) 
            return False 
        return True
    
    def process_solr(self, library, start, rows, sort, fl):
        try:
            solr = self._solr_big_query(
                bibcodes=library.bibcode,
                start=start,
                rows=rows,
                sort=sort,
                fl=fl
            ).json()
        except Exception as error:
            current_app.logger.warning('Could not parse solr data: {0}'
                                    .format(error))
            solr = {'error': 'Could not parse solr data'}
        
        # Now check if we can update the library database based on the
        # returned canonical bibcodes
        if solr.get('response'):
            # Update bibcodes based on solr's response
            updates = self.solr_update_library(
                library_id=library.id,
                solr_docs=solr['response']['docs']
            )

            documents = [doc['bibcode'] for doc in solr['response']['docs']]
        else:
            # Some problem occurred, we will just ignore it, but will
            # definitely log it.
            solr = SOLR_RESPONSE_MISMATCH_ERROR['body']
            current_app.logger.warning('Problem with solr response: {0}'
                                    .format(solr))
            updates = {}
            documents = library.get_bibcodes()
            documents.sort()
            documents = documents[start:start+rows]
        return solr, updates, documents
    
    def process_raw_library(self, user, library, start, rows):
        """
        Processes the request for raw library 
        :param library: library ID
        :param user: user ID 
        :param start: int used to delimit the start of pagination 
        :param rows: int used to delimit the start of pagination 
        :return: solr: str 
                 updates: empty dictionary
                 documents: dictionary with docs in library from start to start + rows
        """
        solr = 'Only the raw library was requested.'
        current_app.logger.info('User: {0} requested only raw library output'
                                    .format(user))
        updates = {}
        documents = library.get_bibcodes()
        documents.sort()
        documents = documents[start:start+rows]
        
        return solr, updates, documents
    
    @classmethod
    def get_notes_from_library(cls, library, session): 
        """
        Get all notes (including orphan notes) from the library 
        :param library: <string>  ID of the library 
        :param session: current session necessary to get notes

        :return: dict of notes with valid bibcode and invalid bibcode in the form {'notes': [], 'orphan_notes': []}    
                 if there are no notes returns {'notes': [], 'orphan_notes': []} 
        """
        # Get all notes from library 
        notes = session.query(Notes).filter(Notes.library_id == library.id).all() 
        # Easy way to get corresponding note to bibcode 
        bibcode_to_notes_map = {note.bibcode: note for note in notes}

        # Since we ran solr_update_library to know if a note is valid or not 
        # We just need to check if its bibcode is in the library 
        # If it's not we're looking at an orphan note. 
        response = {'notes': {}, 'orphan_notes': {}}
        for bibcode in bibcode_to_notes_map.keys():
            if bibcode in set(library.get_bibcodes()): 
                note = bibcode_to_notes_map[bibcode]
                response['notes'][bibcode] = {'id': note.id, 'content': note.content}
            else: 
                note = bibcode_to_notes_map[bibcode]
                response['orphan_notes'][bibcode] = {'id': note.id, 'content': note.content}
        return response

    def process_library_request(self, data):
        """
        Processes the get request for the library and assembles a response
        :param data: <dict> containing user, service_uid, library_id, start, rows, sort, fl, 
                    raw_library, notes and session. 

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
          library_notes:        <dict>    Dictionary of library notes, including orphan 
                                          notes (those not associated with a bibcode in the library)
        """
        
        try:
            library, metadata = self.get_documents_from_library(
                library_id=data["library_id"],
                service_uid=data["service_uid"],
                session=data["session"]
            )
       
            
            if data["raw_library"]:
                solr, updates, documents = self.process_raw_library(data["user"], 
                                                                    library, 
                                                                    data["start"], 
                                                                    data["rows"])
            else:
                solr, updates, documents = self.process_solr(library, 
                                                             data["start"], 
                                                             data["rows"], 
                                                             data["sort"], 
                                                             data["fl"])

            library_notes = {}
            if data["notes"]: 
                library_notes = self.get_notes_from_library(library, data["session"])
            
            # Make the response dictionary
            response = dict(
                documents=documents,
                solr=solr,
                metadata=metadata,
                updates=updates,
            )

            if library_notes and (library_notes.get('notes', {}) or library_notes.get('orphan_notes', {})):
                response['library_notes'] = library_notes

            return library, response, None

        except Exception as error:
            current_app.logger.warning(
                'Library missing or solr endpoint failed: {0}'
                .format(error)
            )
            return data["library_id"], None, err(MISSING_LIBRARY_ERROR)
        
    def is_library_public_or_has_special_token(self, library, request):
        """
        HTTP GET request that returns all the documents inside a given
        user's library
        :param library: library

        :return: <boolean> True if the library is public or if header contains 
        special token
        """

        special_token = current_app.config.get('READONLY_ALL_LIBRARIES_TOKEN')
        return library.public or (
            special_token and request.headers.get('Authorization', '').endswith(special_token)
        )
    
    def handle_no_permission(self, user, service_uid, library):
        """
        Checks if user has permission to access the given library
        :param user: user 
        :param service_uid: user service id 
        :param library: library 

        :return: None if user has permission and an error otherwise
        """
        if not self.check_user_and_access(user, service_uid, library):
            return err(NO_PERMISSION_ERROR)

    def check_user_and_access(self, user, service_uid, library):
        """
        Checks if user exists and has read access to the library
        :param user: user 
        :param service_uid: user service id 
        :param library: library 

        :return: <boolean> True if the user exists and has permissions 
        """
        return self.check_user_has_read_access(service_uid, library) and \
            self.check_user_exists(user, library)
            
    def check_user_exists(self, user, library):
        """
        Checks if user exists
        :param user: user 
        :param library: library 

        :return: <boolean> True if the user exists
        """
        if not self.helper_user_exists(absolute_uid=user):
            current_app.logger.error(
                'User: {0} does not exist in the database. '
                'Therefore will not have extra privileges to view the library: {1}'
                .format(user, library.id)
            )
            return False

        return True

    def check_user_has_read_access(self, service_uid, library):
        """
        Checks if user has read access to library
        :param service_uid: user service id 
        :param library: library 

        :return: <boolean> True if the user has read access to library
        """
        if not self.read_access(service_uid=service_uid, library_id=library.id):
            current_app.logger.error(
                'User: {0} does not have access to library: {1}. DENIED'
                .format(service_uid, library.id)
            )
            return False

        return True

    # Methods
    def get(self, library):
        """
        HTTP GET request that returns all the documents inside a given
        user's library
        :param library: library slug

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
          library_notes:        <dict>    Dictionary of library notes, including orphan 
                                          notes (those not associated with a bibcode in the library)

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

        # Get user 
        user, user_error = self.get_user_id_from_headers(request)
        if user_error: 
            return user_error
        
        # Parameters to be forwarded to Solr: pagination, and fields
        start, rows, sort, fl, raw_library = self.load_parameters(request)

        # Get library id
        library_id, library_error = self.get_library_from_slug(user, library)
        if library_error: 
            return library_error
    
        # If set to True, return notes in library
        notes = request.args.get('notes', type=bool, default=True)
 
        # Get user id for service 
        service_uid = self.get_service_uid(user) 

        # Data needed to process the library request
        data = {"user": user, 
                "service_uid": service_uid, 
                "library_id": library_id,
                "start": start, 
                "rows": rows, 
                "sort": sort, 
                "fl": fl, 
                "raw_library": raw_library,
                "notes": notes}
        
        with current_app.session_scope() as session:
            data['session'] = session
            library, response, solr_error = self.process_library_request(data)
            if solr_error: 
                return solr_error

        # Skip any more logic if the library is public or the exception token is present
        if self.is_library_public_or_has_special_token(library, request):
            current_app.logger.info('Library: {0} is public'
                                    .format(library_id))
            return response, 200
        
        current_app.logger.warning('Library: {0} is private'.format(library_id))
        
        # Check if the user exists and has access to the library
        no_permission = self.handle_no_permission(user, service_uid, library)
        if no_permission: 
            return no_permission

        # If they have access, let them obtain the requested content
        current_app.logger.info('User: {0} has access to library: {1}. '
                                'ALLOWED'
                                .format(user, library_id))
        return response, 200