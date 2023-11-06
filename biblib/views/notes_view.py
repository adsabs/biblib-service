from biblib.utils import err, get_post_data
from biblib.models import Notes
from biblib.views.base_view import BaseView
from flask import request, current_app
from flask_discoverer import advertise
from biblib.views.http_errors import MISSING_USERNAME_ERROR, \
    MISSING_LIBRARY_ERROR, NO_PERMISSION_ERROR, BAD_LIBRARY_ID_ERROR, DUPLICATE_NOTE_ERROR, \
    WRONG_TYPE_ERROR, MISSING_NOTE_ERROR, INVALID_BIBCODE_ERROR, DUPLICATE_NOTE_ERROR, \
    INVALID_CONTENT_ERROR
from biblib.biblib_exceptions import BibcodeNotFoundError, DuplicateNoteError

class NotesView(BaseView):

    decorators = [advertise('scopes', 'rate_limit')]
    scopes = ['user']
    rate_limit = [1000, 60*60*24]

    def get_library_and_metadata_wrapper(self, library_id, service_uid, session): 
        """
        Wrapper to get the library and library metadata 
        :param library_id: the library id 
        :param service_uid: user id 
        :param session: current session 

        :return: library: library information
                 metadata: all the library metadata 
        """
        library, metadata = BaseView.get_library_and_metadata(
                library_id=library_id,
                service_uid=service_uid,
                session=session
            )
        return library, metadata 
    

    def get_note_data(self, document_id, library_id, service_uid):
        """
        Gets note data to be returned in the HTTP GET request
        :param document id: bibcode
        :param library_id: the library id 
        :param service_uid: user id 

        :return: library: library object 
                 metadata: all the library metadata 
                 note: note if found, null if not found
        """
        with current_app.session_scope() as session:
            library, metadata = self.get_library_and_metadata_wrapper(library_id, 
                                                              service_uid, 
                                                              session)
           
            note = session.query(Notes).filter(
                Notes.bibcode == document_id,
                Notes.library_id == library_id
            ).one_or_none()

            if note: 
                note = note.as_dict() 
        return library, metadata, note
    
    def add_note_to_document(self, document_id, library_id, service_uid, note_data):
        """
        Adds note to a document
        :param document id: bibcode
        :param library_id: the library id 
        :param service_uid: user id 
        :param note_data: note content

        :return: library: library object 
                 metadata: all the library metadata 
                 note: note if found, null if not found
        """
        try: 
            with current_app.session_scope() as session:
                library, metadata = self.get_library_and_metadata_wrapper(library_id, 
                                                              service_uid, 
                                                              session)
                
                note = Notes.create_unique(session=session, 
                                            content=note_data.get('content', ''), 
                                            bibcode=document_id, 
                                            library=library)
                session.add(note)
                session.commit()
                note = note.as_dict()
                return note, metadata
        except (BibcodeNotFoundError, DuplicateNoteError, Exception) as e:
            current_app.logger.error('Failed to add note to document {0} in library {1}. Error {2}'
                .format(document_id, library_id, e)
            ) 
            raise 
    
    def delete_note(self, document_id, library_id):
        """
        Deletes note from the database
        :param document id: bibcode
        :param library_id: the library id 
        
        :return: <bool> True if deleted, False if note not found
        """
        
        with current_app.session_scope() as session:
            note = session.query(Notes).filter_by(bibcode=document_id, library_id=library_id).one_or_none()
            if note:
                session.delete(note)
                session.commit()
                return True 
            
            return False 
        
    def update_note(self, library_id, document_id, library_data): 
        """
        Updates note
        :param document id: bibcode
        :param library_id: the library id 
        
        :return: note if updated, null if note not found
        """
        new_content = library_data.get('content', None)

        if new_content is None: 
            raise ValueError

        with current_app.session_scope() as session: 
            note = session.query(Notes).filter_by(bibcode=document_id, library_id=library_id).one_or_none()
            if note: 
                note.content = new_content 
                session.add(note)
                session.commit() 
                return note.as_dict() 
            

   
    def get(self, library,  document_id):
        """
        HTTP GET request that gets a note from the library
        :param library: library ID
        :param document_id: bibcode

        :return: note if present in the library

        Header:
        -------
        Must contain the API forwarded user ID of the user accessing the end
        point

        Post-body:
        ---------
        No data 

        Return data:
        -----------
        returns the note

        Permissions:
        -----------
        The following type of user can update the content:

          - owner
          - admin
          - read
        """

        try: 
            # Get user 
            user = self.helper_get_user_id()
            current_app.logger.info('User: {0} requested library: {1}'
                                    .format(user, library))
            # Get library id
            library_id = self.helper_slug_to_uuid(library)

            if not self.helper_library_exists(library_id):
                return err(MISSING_LIBRARY_ERROR)
            
            # Get user id for service 
            service_uid = self.helper_absolute_uid_to_service_uid(absolute_uid=user)
            
            # Get library, library metadata and note to be returned
            library, metadata, note = self.get_note_data(document_id, library_id, service_uid)

            if not note: 
                return err(MISSING_NOTE_ERROR)
            
            current_app.logger.info('Note found: {0}'
                                    .format(note))
            
            response = dict(document=document_id, 
                            note=note, 
                            library_metadata=metadata)
            
            current_app.logger.info('Checking if library {0} is public'
                                .format(library))
            # If library is public or has special token anyone can access it 
            if self.helper_is_library_public_or_has_special_token(library, request):
                return response, 200 
                
            # If user does not exist they don't have access to this private library
            if not self.helper_user_exists(user):
                current_app.logger.error(
                    'User: {0} does not exist in the database. '
                    'Therefore will not have extra privileges to view the library: {1}'
                    .format(user, library_id)
                )
                return err(NO_PERMISSION_ERROR)
            
            # Check if the user has read access to this private library
            if not self.helper_check_user_has_read_access(service_uid, library): 
                return err(NO_PERMISSION_ERROR)
            
            current_app.logger.info('Getting note for document {0} in library {1}.'.format(document_id, library_id))
                
            return response, 200 
        except ValueError: 
            return err(BAD_LIBRARY_ID_ERROR)
        except KeyError:
            return err(MISSING_USERNAME_ERROR)
        except TypeError:
            return err(BAD_LIBRARY_ID_ERROR)
        

    def post(self, library, document_id):
        """
        HTTP POST request that adds a note to the library
        :param library: library ID
        :param document_id: bibcode

        :return: the newly created note

        Header:
        -------
        Must contain the API forwarded user ID of the user accessing the end
        point

        Post-body:
        ---------
        content: <str> new note content, can be empty string 

        Return data:
        -----------
        returns the created note

        Permissions:
        -----------
        The following type of user can update the content:

          - owner
          - admin
          - write
        """
        try:
            user = self.helper_get_user_id()
        except KeyError:
            return err(MISSING_USERNAME_ERROR)

        current_app.logger.info('User: {0} requested library: {1}'
                                .format(user, library))
        # Get library id
        try:
            library_id = self.helper_slug_to_uuid(library)
        except TypeError:
            return err(BAD_LIBRARY_ID_ERROR)
        
        if not self.helper_user_exists(user):
            return err(NO_PERMISSION_ERROR)

        if not self.helper_library_exists(library_id):
            return err(MISSING_LIBRARY_ERROR)
        
        # Get user id for service 
        service_uid = self.helper_absolute_uid_to_service_uid(absolute_uid=user)

        # Check the user's permissions
        if not self.write_access(service_uid=service_uid,
                                library_id=library_id):
            return err(NO_PERMISSION_ERROR)
        
        try:
            data = get_post_data(
                request,
                types=dict(params=dict, action=str)
            )
            current_app.logger.info('{}'
                                .format(data))

        except TypeError as error:
            current_app.logger.error('Wrong type passed for POST: {0} [{1}]'
                                    .format(request.data, error))
            return err(WRONG_TYPE_ERROR)
        
        try: 
            note, metadata = self.add_note_to_document(document_id, 
                                                 library_id, 
                                                 service_uid, 
                                                 data)
            
            response = dict(note=note, 
                            library_metadata=metadata)
            
            return response, 201
        except BibcodeNotFoundError: 
            return err(INVALID_BIBCODE_ERROR)
        except DuplicateNoteError: 
            return err(DUPLICATE_NOTE_ERROR)
        except Exception as error: 
            return current_app.logger.error('Error: {0}'
                                    .format(error))
        
        
    
    def put(self, library, document_id):
        """
        HTTP PUT request that updates a note of the library
        :param library: library ID
        :param document_id: bibcode

        :return: the updated note 

        Header:
        -------
        Must contain the API forwarded user ID of the user accessing the end
        point

        Post-body:
        ---------
        content: new note content, can be empty string 

        Return data:
        -----------
        returns the updated note

        Permissions:
        -----------
        The following type of user can update the content:

          - owner
          - admin
        """
        try:
            user = self.helper_get_user_id()
        except KeyError:
            return err(MISSING_USERNAME_ERROR)

        current_app.logger.info('User: {0} requested library: {1}'
                                .format(user, library))
        # Get library id
        try:
            library_id = self.helper_slug_to_uuid(library)
        except TypeError:
            return err(BAD_LIBRARY_ID_ERROR)
        
        if not self.helper_user_exists(user):
            return err(NO_PERMISSION_ERROR)

        if not self.helper_library_exists(library_id):
            return err(MISSING_LIBRARY_ERROR)
        
        # Get user id for service 
        service_uid = self.helper_absolute_uid_to_service_uid(absolute_uid=user)

        # Check the user's permissions
        if not self.update_access(service_uid=service_uid,
                                library_id=library_id):
            return err(NO_PERMISSION_ERROR)
        
        try:
            data = get_post_data(
                request,
                types=dict(params=dict, action=str)
            )
            current_app.logger.info('{}'
                                .format(data))
        except TypeError as error:
            current_app.logger.error('Wrong type passed for PUT: {0} [{1}]'
                                    .format(request.data, error))
            return err(WRONG_TYPE_ERROR)
        
        try: 
            response = self.update_note(library_id, document_id, data)
            if not response: 
                return err(MISSING_NOTE_ERROR)
        except ValueError: 
            return err(INVALID_CONTENT_ERROR)
        
        return response, 200
    
    
    def delete(self, library, document_id):
        """
        HTTP DELETE request that deletes a note from the library
        :param library: library ID
        :param document_id: bibcode

        :return: empty response if successful

        Header:
        -------
        Must contain the API forwarded user ID of the user accessing the end
        point

        Post-body:
        ---------
        No post content accepted.

        Return data:
        -----------
        No data

        Permissions:
        -----------
        The following type of user can delete the note:
          - owner
        """
        try:
            user = self.helper_get_user_id()
        except KeyError:
            return err(MISSING_USERNAME_ERROR)

        current_app.logger.info('User: {0} requested library: {1}'
                                .format(user, library))
        # Get library id
        try:
            library_id = self.helper_slug_to_uuid(library)
        except TypeError:
            return err(BAD_LIBRARY_ID_ERROR)
        
        if not self.helper_user_exists(user):
            return err(NO_PERMISSION_ERROR)
        
        if not self.helper_library_exists(library_id):
            return err(MISSING_LIBRARY_ERROR)
        
        # Get user id for service 
        service_uid = self.helper_absolute_uid_to_service_uid(absolute_uid=user)

        
        current_app.logger.info('user_API: {0:d} '
                                'requesting to delete note for document {1} and library {2}.'
                                .format(service_uid, document_id, library))

        if not self.delete_access(service_uid=service_uid,
                                library_id=library_id):
            return err(NO_PERMISSION_ERROR)
        
        note_was_deleted = self.delete_note(document_id, 
                                    library_id)
        if not note_was_deleted: 
            return err(MISSING_NOTE_ERROR)
        
        return {}, 200
        

        
      