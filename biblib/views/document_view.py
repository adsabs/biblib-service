"""
Document view
"""

from ..utils import err, get_post_data
from ..models import Library, Permissions
from .base_view import BaseView
from ..client import client
from flask import request, current_app
from flask_discoverer import advertise
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import Boolean
from .http_errors import MISSING_USERNAME_ERROR, DUPLICATE_LIBRARY_NAME_ERROR, \
    WRONG_TYPE_ERROR, NO_PERMISSION_ERROR, MISSING_LIBRARY_ERROR, BAD_LIBRARY_ID_ERROR, INVALID_BIBCODE_SPECIFIED_ERROR
from ..biblib_exceptions import PermissionDeniedError


class DocumentView(BaseView):
    """
    End point to interact with a specific library, by adding documents and
    removing documents. You also use this endpoint to delete the entire
    library as this method should be scoped.
    """
    # TODO: adding tags using PUT for RESTful endpoint?

    decorators = [advertise('scopes', 'rate_limit')]
    scopes = ['user']
    rate_limit = [1000, 60*60*24]

    @classmethod
    def add_document_to_library(cls, library_id, document_data):
        """
        Adds a document to a user's library
        :param library_id: the library id to update
        :param document_data: the meta data of the document

        :return: number_added: number of documents successfully added
        """
        current_app.logger.info('Adding a document: {0} to library_uuid: {1}'
                                .format(document_data, library_id))

        with current_app.session_scope() as session:
            # Find the specified library
            library = session.query(Library).filter_by(id=library_id).one()

            start_length = len(library.bibcode)

            #Validate supplied bibcodes to confirm they exist in SOLR
            valid_bibcodes = []
            page_size = min(current_app.config.get('BIGQUERY_MAX_ROWS', len(document_data['bibcode'])), len(document_data['bibcode']))
            #Check if there are more than the allowed number of bibcodes. Iterate over all pages if needed.
            pages = len(document_data['bibcode']) // page_size + (len(document_data['bibcode']) % page_size > 0)
            
            for page in range(0, pages):
                solr_resp, status_code = cls.query_valid_bibcodes(document_data['bibcode'], start=page*page_size, rows=min(page_size, len(document_data['bibcode'])))

                if "error" in solr_resp.keys():
                    #If SOLR request fails, pass the error back to the user
                    current_app.logger.error("Failed to retrieve bibcodes with error: {}".format(solr_resp.get("error")))
                    output_dict = {"error": solr_resp.get("error"), "number_added": 0, "status": status_code}
                    valid_bibcodes += []
                    return output_dict
                else:
                    #If SOLR query succeeds generate list of valid bibcodes from response
                    add_bibcodes = [doc.get('bibcode') for doc in solr_resp.get('docs', {})]
                    if add_bibcodes:
                        valid_bibcodes += add_bibcodes
                        current_app.logger.debug("Found the following valid bibcodes: {}".format(add_bibcodes))
                    #Added additional checks to prevent unnecessary calls to bigquery.
                    else:
                        current_app.logger.debug("query returned no new bibcodes. Halting paging.")
                        break
                    if len(add_bibcodes) < current_app.config.get('BIGQUERY_MAX_ROWS'):
                        current_app.logger.debug("Bigquery returned less than max row number of bibcodes. Assuming all valid bibcodes are accounted for.")
                        break
                         
            
            if valid_bibcodes:
                #Add all valid bibcodes to library
                library.add_bibcodes(valid_bibcodes)

                session.add(library)
                session.commit()

                current_app.logger.info('Added: {0} to {1}'.format(
                    valid_bibcodes,
                    library_id)
                )
                
                current_app.logger.debug('Added: {0} is now {1}'.format(
                    valid_bibcodes,
                    library.bibcode)
                )
            
            end_length = len(library.bibcode)

            #Generate a list of invalid bibcodes
            invalid_bibcodes = list(set(document_data['bibcode']) - set(valid_bibcodes))
            
            #Generate output that contains the number added and the number of invalid bibcodes.
            output_dict = {"number_added": end_length - start_length}
            if invalid_bibcodes: output_dict['invalid_bibcodes'] = invalid_bibcodes
            
            return  output_dict


    @classmethod
    def query_valid_bibcodes(cls, input_bibcodes, start, rows):
        """
        Takes a list of input bibcodes and validates there existence in ADS
        through the API. Calls either standard search or bigquery depending 
        on the query length.
        """
        bigquery_min = current_app.config.get('BIBLIB_SOLR_BIG_QUERY_MIN', 10)
        if len(input_bibcodes) < bigquery_min:
            try:
                response = cls.standard_ADS_bibcode_query(input_bibcodes)
                solr_resp = response.json()
                status = response.status_code
            except Exception as err:
                current_app.logger.error("Failed to collect valid bibcodes from input due to internal error: {}.".format(err))
                solr_resp = {"response": {"error": "An internal error occurred when querying SOLR. Please try again later."}}
                status = 500
        else:
            try:
                #For calls to bigquery, we limit the number of rows allowed in config.
                response = cls.solr_big_query(input_bibcodes, start=start, rows=rows)
                solr_resp = response.json()
                status = response.status_code
            except Exception as err:
                current_app.logger.error("Failed to collect valid bibcodes from input due to internal error: {}".format(err))
                solr_resp = {"response": {"error": "An internal error occurred when querying SOLR. Please try again later."}}
                status = 500

        return solr_resp.get("response"), status
    
    @classmethod
    def remove_documents_from_library(cls, library_id, document_data):
        """
        Remove a given document from a specific library

        :param library_id: the unique ID of the library
        :param document_data: the meta data of the document

        :return: number_removed: number of documents successfully removed
        """
        current_app.logger.info('Removing a document: {0} from library_uuid: '
                                '{1}'.format(document_data, library_id))
        with current_app.session_scope() as session:
            library = session.query(Library).filter_by(id=library_id).one()
            start_length = len(library.bibcode)

            library.remove_bibcodes(document_data['bibcode'])

            session.add(library)
            session.commit()
            current_app.logger.info('Removed document successfully: {0}'
                                    .format(library.bibcode))
            end_length = len(library.bibcode)

            return start_length - end_length

    @staticmethod
    def update_library(library_id, library_data):
        """
        Update the meta data of the library
        :param library_id: the unique ID of the library
        :param library_data: dictionary containing the updateable values

        :return: values updated
        """
        updateable = ['name', 'description', 'public']
        updated = {}

        with current_app.session_scope() as session:
            library = session.query(Library).filter_by(id=library_id).one()

            for key in library_data:
                if key not in updateable:
                    continue
                setattr(library, key, library_data[key])
                updated[key] = library_data[key]

            session.add(library)
            session.commit()

        return updated

    @staticmethod
    def delete_library(library_id):
        """
        Delete the entire library from the database
        :param library_id: the unique ID of the library

        :return: no return
        """

        with current_app.session_scope() as session:
            library = session.query(Library).filter_by(id=library_id).one()
            session.delete(library)
            session.commit()

    @classmethod
    def update_access(cls, service_uid, library_id):
        """
        Defines which type of user has delete permissions to a library.

        :param service_uid: the user ID within this microservice
        :param library_id: the unique ID of the library

        :return: boolean, access (True), no access (False)
        """
        update_allowed = ['admin', 'owner']
        for access_type in update_allowed:
            if cls.helper_access_allowed(service_uid=service_uid,
                                         library_id=library_id,
                                         access_type=access_type):
                return True

        return False

    @classmethod
    def delete_access(cls, service_uid, library_id):
        """
        Defines which type of user has delete permissions to a library.

        :param service_uid: the user ID within this microservice
        :param library_id: the unique ID of the library

        :return: boolean, access (True), no access (False)
        """
        delete_allowed = cls.helper_access_allowed(service_uid=service_uid,
                                                   library_id=library_id,
                                                   access_type='owner')
        return delete_allowed

    @classmethod
    def write_access(cls, service_uid, library_id):
        """
        Defines which type of user has write permissions to a library.

        :param service_uid: the user ID within this microservice
        :param library_id: the unique ID of the library

        :return: boolean, access (True), no access (False)
        """

        read_allowed = ['write', 'admin', 'owner']
        for access_type in read_allowed:
            if cls.helper_access_allowed(service_uid=service_uid,
                                         library_id=library_id,
                                         access_type=access_type):
                return True

        return False

    @staticmethod
    def library_name_exists(service_uid, library_name):
        """
        Checks to see if a library name already exists in the user's created
        libraries

        :param service_uid: the user ID within this microservice
        :param library_name: name to check if it exists

        :return: True (exists), False (does not exist)
        """

        with current_app.session_scope() as session:
            library_names = \
                [i.library.name for i in
                 session.query(Permissions)\
                     .filter_by(user_id = service_uid)\
                     .filter(Permissions.permissions['owner'].astext.cast(Boolean).is_(True)).all()]

        if library_name in library_names:
            current_app.logger.error('Name supplied for the library already '
                                     'exists: "{0}"'.format(library_name))

            return True
        else:
            return False

    def post(self, library):
        """
        HTTP POST request that adds a document to a library for a given user
        :param library: library ID

        :return: the response for if the library was successfully created

        Header:
        -------
        Must contain the API forwarded user ID of the user accessing the end
        point

        Post body:
        ----------
        KEYWORD, VALUE

        bibcode:  <list>          List of bibcodes to be added
        action:   add, remove     add - adds a bibcode, remove - removes a
                                  bibcode

        Return data:
        -----------
        number_added: number of documents added (if 'add' is used)
        number_removed: number of documents removed (if 'remove' is used)

        Permissions:
        -----------
        The following type of user can add documents:
          - owner
          - admin
          - write
        """
        # Get the user requesting this from the header
        try:
            user_editing = self.helper_get_user_id()
        except KeyError:
            return err(MISSING_USERNAME_ERROR)

        # URL safe base64 string to UUID
        try:
            library = self.helper_slug_to_uuid(library)
        except TypeError:
            return err(BAD_LIBRARY_ID_ERROR)

        user_editing_uid = \
            self.helper_absolute_uid_to_service_uid(absolute_uid=user_editing)

        # Check the permissions of the user
        if not self.write_access(service_uid=user_editing_uid,
                                 library_id=library):
            return err(NO_PERMISSION_ERROR)

        try:
            data = get_post_data(
                request,
                types=dict(bibcode=list, action=str)
            )
        except TypeError as error:
            current_app.logger.error('Wrong type passed for POST: {0} [{1}]'
                                     .format(request.data, error))
            return err(WRONG_TYPE_ERROR)

        if data['action'] == 'add':
            current_app.logger.info('User requested to add a document')
            output = self.add_document_to_library(
                library_id=library,
                document_data=data
            )
            if "error" in output.keys():
                return err(dict(body=output.get("error"), number=output.get("status_code", 400)))

            elif "invalid_bibcodes" in output.keys():
                #Returns the list of invalid bibcodes, but only returns 400 if no bibcodes were added.
                if output.get('number_added') != 0:
                    return {"invalid_identifiers": output.get("invalid_bibcodes"), "number_added": output.get('number_added')}, 200
                else:
                    return err(INVALID_BIBCODE_SPECIFIED_ERROR(output))

            else:
                current_app.logger.info(
                    'Successfully added {0} documents to {1} by {2}'
                    .format(output.get("number_added"), library, user_editing_uid)
                )
                return {'number_added': output.get("number_added")}, 200

        elif data['action'] == 'remove':
            current_app.logger.info('User requested to remove a document')
            number_removed = self.remove_documents_from_library(
                library_id=library,
                document_data=data
            )
            current_app.logger.info(
                'Successfully removed {0} documents to {1} by {2}'
                .format(number_removed, library, user_editing_uid)
                )
            return {'number_removed': number_removed}, 200

        else:
            current_app.logger.info('User requested a non-standard action')
            return {}, 400

    def put(self, library):
        """
        HTTP PUT request that updates the meta-data of the library
        :param library: library ID

        :return: the response for if the library was updated

        Header:
        -------
        Must contain the API forwarded user ID of the user accessing the end
        point

        Post-body:
        ---------
        name: name of the library
        description: description of the library
        public: boolean

        Note: The above are optional, they can be empty if needed.

        Return data:
        -----------
        returns the key/value that was requested to be updated

        Permissions:
        -----------
        The following type of user can update the 'name', 'library', and
        'public':

          - owner
          - admin
        """
        try:
            user = self.helper_get_user_id()
        except KeyError:
            return err(MISSING_USERNAME_ERROR)

        # URL safe base64 string to UUID
        try:
            library = self.helper_slug_to_uuid(library)
        except TypeError:
            return err(BAD_LIBRARY_ID_ERROR)

        if not self.helper_user_exists(user):
            return err(NO_PERMISSION_ERROR)

        if not self.helper_library_exists(library):
            return err(MISSING_LIBRARY_ERROR)

        user_updating_uid = \
            self.helper_absolute_uid_to_service_uid(absolute_uid=user)

        if not self.update_access(service_uid=user_updating_uid,
                                  library_id=library):
            return err(NO_PERMISSION_ERROR)

        try:
            library_data = get_post_data(
                request,
                types=dict(
                    name=str,
                    description=str,
                    public=bool
                )
            )
        except TypeError as error:
            current_app.logger.error('Wrong type passed for POST: {0} [{1}]'
                                     .format(request.data, error))
            return err(WRONG_TYPE_ERROR)

        # Remove content that is empty (note that the list() is necessary to create a copy, so pop will work)
        for key in list(library_data.keys()):
            if library_data[key] == ''.strip(' '):
                current_app.logger.warning('Removing key: {0} as its empty.'
                                           .format(key))
                library_data.pop(key)

        # Check for duplicate namaes
        if 'name' in library_data and \
                self.library_name_exists(service_uid=user_updating_uid,
                                         library_name=library_data['name']):

                return err(DUPLICATE_LIBRARY_NAME_ERROR)

        response = self.update_library(library_id=library,
                                       library_data=library_data)

        return response, 200

    def delete(self, library):
        """
        HTTP DELETE request that deletes a library defined by the number passed
        :param library: library ID

        :return: the response for it the library was deleted

        Header:
        -------
        Must contain the API forwarded user ID of the user accessing the end
        point

        Post-body:
        ----------
        No post content accepted.

        Return data:
        -----------
        No data

        Permissions:
        -----------
        The following type of user can update a library:
          - owner
        """
        try:
            user = self.helper_get_user_id()
        except KeyError:
            return err(MISSING_USERNAME_ERROR)

        # URL safe base64 string to UUID
        try:
            library = self.helper_slug_to_uuid(library)
        except TypeError:
            return err(BAD_LIBRARY_ID_ERROR)

        if not self.helper_user_exists(user):
            return err(NO_PERMISSION_ERROR)

        if not self.helper_library_exists(library):
            return err(MISSING_LIBRARY_ERROR)

        user_deleting_uid = \
            self.helper_absolute_uid_to_service_uid(absolute_uid=user)

        try:
            current_app.logger.info('user_API: {0:d} '
                                    'requesting to delete library: {1}'
                                    .format(user_deleting_uid, library))

            if self.delete_access(service_uid=user_deleting_uid,
                                  library_id=library):
                self.delete_library(library_id=library)
                current_app.logger.info('User: {0} deleted library: {1}.'
                                        .format(user_deleting_uid,
                                                library))
            else:
                current_app.logger.error('User: {0} has incorrect permissions '
                                         'to delete: {1}.'
                                         .format(user_deleting_uid,
                                                 library))
                raise PermissionDeniedError('Incorrect permissions')

        except NoResultFound as error:
            current_app.logger.info('Failed to delete: {0}'.format(error))
            return err(MISSING_LIBRARY_ERROR)

        except PermissionDeniedError as error:
            current_app.logger.info('Failed to delete: {0}'.format(error))
            return err(NO_PERMISSION_ERROR)

        return {}, 200
