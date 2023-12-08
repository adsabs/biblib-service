"""
Operations view
"""
from biblib.views import USER_ID_KEYWORD
from biblib.utils import err, get_post_data
from biblib.models import User, Library, Permissions
from biblib.client import client
from biblib.views.base_view import BaseView
from adsmutils import get_date
from flask import request, current_app
from flask_discoverer import advertise
from sqlalchemy.orm.exc import NoResultFound
from biblib.views.http_errors import MISSING_USERNAME_ERROR, SOLR_RESPONSE_MISMATCH_ERROR, \
    MISSING_LIBRARY_ERROR, NO_PERMISSION_ERROR, DUPLICATE_LIBRARY_NAME_ERROR, \
    WRONG_TYPE_ERROR, NO_LIBRARY_SPECIFIED_ERROR, TOO_MANY_LIBRARIES_SPECIFIED_ERROR, BAD_LIBRARY_ID_ERROR
from biblib.biblib_exceptions import BackendIntegrityError


class OperationsView(BaseView):
    """
    Endpoint to conduct operations on a given library or set of libraries. Supported operations are
    union, intersection, difference, copy, and empty.
    """
    decorators = [advertise('scopes', 'rate_limit')]
    scopes = ['user']
    rate_limit = [1000, 60 * 60 * 24]

    @classmethod
    def setops_libraries(cls, library_id, document_data, operation='union'):
        """
        Takes the union of two or more libraries
        :param library_id: the primary library ID
        :param document_data: dict containing the list 'libraries' that holds the secondary library IDs

        :return: list of bibcodes in the union set
        """
        current_app.logger.info('User requested to take the {0} of {1} with {2}'
                                .format(operation, library_id, document_data['libraries']))
        with current_app.session_scope() as session:
            # Find the specified library
            primary_library = session.query(Library).filter_by(id=library_id).one()
            out_lib = set(primary_library.get_bibcodes())

            for lib in document_data['libraries']:
                if isinstance(lib, str):
                    lib = cls.helper_slug_to_uuid(lib)
                secondary_library = session.query(Library).filter_by(id=lib).one()
                if operation == 'union':
                    out_lib = out_lib.union(set(secondary_library.get_bibcodes()))
                elif operation == 'intersection':
                    out_lib = out_lib.intersection(set(secondary_library.get_bibcodes()))
                elif operation == 'difference':
                    out_lib = out_lib.difference(set(secondary_library.get_bibcodes()))
                else:
                    current_app.logger.warning('Requested operation {0} is not allowed.'.format(operation))
                    return

        if len(out_lib) < 1:
            current_app.logger.info('No records remain after taking the {0} of {1} and {2}'
                                    .format(operation, library_id, document_data['libraries']))

        return list(out_lib)

    @classmethod
    def copy_library(cls, library_id, document_data):
        """
        Copies the contents of one library into another. Does not empty library first; call
        empty_library on the target library first to do so
        :param library_id: primary library ID, library to copy
        :param document_data: dict containing the list 'libraries' which holds one secondary library ID; this is
            the library to copy over

        :return: dict containing the metadata of the copied-over library (the secondary library)
        """
        current_app.logger.info('User requested to copy the contents of {0} into {1}'
                                .format(library_id, document_data['libraries']))

        secondary_libid = document_data['libraries'][0]
        if isinstance(secondary_libid, str):
            secondary_libid = cls.helper_slug_to_uuid(secondary_libid)

        metadata = {}
        with current_app.session_scope() as session:
            primary_library = session.query(Library).filter_by(id=library_id).one()
            good_bib = primary_library.get_bibcodes()

            secondary_library = session.query(Library).filter_by(id=secondary_libid).one()
            secondary_library.add_bibcodes(good_bib)

            metadata['name'] = secondary_library.name
            metadata['description'] = secondary_library.description
            metadata['public'] = secondary_library.public

            session.add(secondary_library)
            session.commit()

        return metadata

    @staticmethod
    def empty_library(library_id):
        """
        Empties the contents of one library
        :param library_id: library to empty

        :return: dict containing the metadata of the emptied library
        """
        current_app.logger.info('User requested to empty the contents of {0}'.format(library_id))

        metadata = {}
        with current_app.session_scope() as session:
            lib = session.query(Library).filter_by(id=library_id).one()
            lib.remove_bibcodes(lib.get_bibcodes())

            metadata['name'] = lib.name
            metadata['description'] = lib.description
            metadata['public'] = lib.public

            session.add(lib)
            session.commit()

        return metadata

    def post(self, library):
        """
        HTTP POST request that conducts operations at the library level.

        :param library: primary library ID
        :return: response if operation was successful

        Header:
        -------
        Must contain the API forwarded user ID of the user accessing the end
        point

        Post body:
        ----------
        KEYWORD, VALUE

        libraries: <list>   List of secondary libraries to include in the action (optional, based on action)
        action: <unicode>   union, intersection, difference, copy, empty
                            Actions to perform on given libraries:
                                Union: requires one or more secondary libraries to be passed; takes the union of the
                                    primary and secondary library sets; a new library is created
                                Intersection: requires one or more secondary libraries to be passed; takes the
                                    intersection of the primary and secondary library sets; a new library is created
                                Difference: requires one or more secondary libraries to be passed; takes the difference
                                    between the primary and secondary libraries; the primary library comes first in the
                                    operation, so the secondary library is removed from the primary; a new library
                                    is created
                                Copy: requires one and only one secondary library to be passed; the primary library
                                    will be copied into the secondary library (so the secondary library will be
                                    overwritten); no new library is created
                                Empty: secondary libraries are ignored; the primary library will be emptied of its
                                    contents, though the library and metadata will remain; no new library is created
        name: <string>      (optional) name of the new library (must be unique for that user); used only for actions in
                                [union, intersection, difference]
        description: <string> (optional) description of the new library; used only for actions in
                                [union, intersection, difference]
        public: <boolean>   (optional) is the new library public to view; used only for actions in
                                [union, intersection, difference]

        -----------
        Return data:
        -----------
        name:           <string>    Name of the library
        id:             <string>    ID of the library
        description:    <string>    Description of the library

        Permissions:
        -----------
        The following type of user can conduct library operations:
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
            library_uuid = self.helper_slug_to_uuid(library)
        except TypeError:
            return err(BAD_LIBRARY_ID_ERROR)

        user_editing_uid = \
            self.helper_absolute_uid_to_service_uid(absolute_uid=user_editing)
        try:
            data = get_post_data(
                request,
                types=dict(libraries=list, action=str, name=str, description=str, public=bool)
            )
        except TypeError as error:
            current_app.logger.error('Wrong type passed for POST: {0} [{1}]'
                                     .format(request.data, error))
            return err(WRONG_TYPE_ERROR)
        
        if data['action'] != 'copy' and not self.write_access(service_uid=user_editing_uid,
                                 library_id=library_uuid):
            return err(NO_PERMISSION_ERROR)
    
       
        has_read_access_primary = False
        has_read_access_secondary = False 
        has_write_access_secondary = False
        primary_is_public = False 
        secondary_is_public = False 
        
        lib_names = []

        with current_app.session_scope() as session:
            primary = session.query(Library).filter_by(id=library_uuid).one()
            lib_names.append(primary.name)
            if primary.public: primary_is_public = True
            if self.read_access(service_uid=user_editing_uid,
                                        library_id=library_uuid):
                has_read_access_primary = True 
        
            for lib in data.get('libraries', []):
                try:
                    secondary_uuid = self.helper_slug_to_uuid(lib)
                except TypeError:
                    return err(BAD_LIBRARY_ID_ERROR)
                secondary = session.query(Library).filter_by(id=secondary_uuid).one()
                if secondary.public: secondary_is_public = True
                lib_names.append(secondary.name)
                if self.read_access(service_uid=user_editing_uid,
                                    library_id=secondary_uuid):
                    has_read_access_secondary = True  
                if self.write_access(service_uid=user_editing_uid,
                            library_id=secondary_uuid): 
                    has_write_access_secondary = True 
                    
                    
            if data['action'] in ['union', 'intersection', 'difference']:
                if 'libraries' not in data:
                    return err(NO_LIBRARY_SPECIFIED_ERROR)
                if not (secondary_is_public or has_read_access_secondary) or not has_read_access_primary: 
                    return err(NO_PERMISSION_ERROR)
                if 'name' not in data:
                    data['name'] = 'Untitled {0}.'.format(get_date().isoformat())
                if 'public' not in data:
                    data['public'] = False

            if data['action'] == 'copy':
                
                if 'libraries' not in data:
                    return err(NO_LIBRARY_SPECIFIED_ERROR)
                if len(data['libraries']) > 1:
                    return err(TOO_MANY_LIBRARIES_SPECIFIED_ERROR)
                # Check the permissions of the user
                if not (primary_is_public or has_read_access_primary) or not has_write_access_secondary:
                    return err(NO_PERMISSION_ERROR)           

        

        if data['action'] == 'union':
            bib_union = self.setops_libraries(
                library_id=library_uuid,
                document_data=data,
                operation='union'
            )

            current_app.logger.info('Successfully took the union of the libraries {0} (IDs: {1}, {2})'
                    .format(', '.join(lib_names), library, ', '.join(data['libraries'])))

            data['bibcode'] = bib_union
            if 'description' not in data:
                description = 'Union of libraries {0} (IDs: {1}, {2})' \
                    .format(', '.join(lib_names), library, ', '.join(data['libraries']))
                # field length capped in model
                if len(description) > 200:
                    description = 'Union of library {0} (ID: {1}) with {2} other libraries'\
                        .format(lib_names[0], library, len(lib_names[1:]))

                data['description'] = description

            try:
                library_dict = self.create_library(service_uid=user_editing_uid, library_data=data)
            except BackendIntegrityError as error:
                current_app.logger.error(error)
                return err(DUPLICATE_LIBRARY_NAME_ERROR)
            except TypeError as error:
                current_app.logger.error(error)
                return err(WRONG_TYPE_ERROR)

            return library_dict, 200

        elif data['action'] == 'intersection':
            bib_intersect = self.setops_libraries(
                library_id=library_uuid,
                document_data=data,
                operation='intersection'
            )
            current_app.logger.info('Successfully took the intersection of the libraries {0} (IDs: {1}, {2})'
                    .format(', '.join(lib_names), library, ', '.join(data['libraries'])))

            data['bibcode'] = bib_intersect
            if 'description' not in data:
                description = 'Intersection of {0} (IDs: {1}, {2})' \
                    .format(', '.join(lib_names), library, ', '.join(data['libraries']))
                if len(description) > 200:
                    description = 'Intersection of {0} (ID: {1}) with {2} other libraries'\
                        .format(lib_names[0], library, len(lib_names[1:]))

                data['description'] = description

            try:
                library_dict = self.create_library(service_uid=user_editing_uid, library_data=data)
            except BackendIntegrityError as error:
                current_app.logger.error(error)
                return err(DUPLICATE_LIBRARY_NAME_ERROR)
            except TypeError as error:
                current_app.logger.error(error)
                return err(WRONG_TYPE_ERROR)
            return library_dict, 200

        elif data['action'] == 'difference':
            bib_diff = self.setops_libraries(
                library_id=library_uuid,
                document_data=data,
                operation='difference'
            )
            current_app.logger.info('Successfully took the difference of {0} (ID {2}) - (minus) {1} (ID {3})'
                    .format(lib_names[0], ', '.join(lib_names[1:]), library, ', '.join(data['libraries'])))

            data['bibcode'] = bib_diff
            if 'description' not in data:
                data['description'] = 'Records that are in {0} (ID {2}) but not in {1} (ID {3})' \
                    .format(lib_names[0], ', '.join(lib_names[1:]), library, ', '.join(data['libraries']))

            try:
                library_dict = self.create_library(service_uid=user_editing_uid, library_data=data)
            except BackendIntegrityError as error:
                current_app.logger.error(error)
                return err(DUPLICATE_LIBRARY_NAME_ERROR)
            except TypeError as error:
                current_app.logger.error(error)
                return err(WRONG_TYPE_ERROR)
            return library_dict, 200

        elif data['action'] == 'copy':
            library_dict = self.copy_library(
                library_id=library_uuid,
                document_data=data
            )
            current_app.logger.info('Successfully copied {0} (ID {2}) into {1} (ID {3})'
                                    .format(lib_names[0], lib_names[1], library, data['libraries'][0]))

            with current_app.session_scope() as session:
                libid = self.helper_slug_to_uuid(data['libraries'][0])
                library = session.query(Library).filter_by(id=libid).one()
                bib = library.get_bibcodes()

                library_dict['bibcode'] = bib

            return library_dict, 200

        elif data['action'] == 'empty':
            library_dict = self.empty_library(
                library_id=library_uuid
            )
            current_app.logger.info('Successfully emptied {0} (ID {1}) of all records'
                                    .format(lib_names[0], library))

            with current_app.session_scope() as session:
                library = session.query(Library).filter_by(id=library_uuid).one()
                bib = library.get_bibcodes()

                library_dict['bibcode'] = bib

            return library_dict, 200

        else:
            current_app.logger.info('User requested a non-standard operation')
            return {}, 400