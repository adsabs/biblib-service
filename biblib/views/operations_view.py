"""
Operations view
"""
from ..views import USER_ID_KEYWORD
from ..utils import err, get_post_data
from ..models import User, Library, Permissions
from ..client import client
from base_view import BaseView
from adsmutils import get_date
from flask import request, current_app
from flask_discoverer import advertise
from sqlalchemy.orm.exc import NoResultFound
from http_errors import MISSING_USERNAME_ERROR, SOLR_RESPONSE_MISMATCH_ERROR, \
    MISSING_LIBRARY_ERROR, NO_PERMISSION_ERROR, DUPLICATE_LIBRARY_NAME_ERROR, \
    WRONG_TYPE_ERROR, NO_LIBRARY_SPECIFIED_ERROR, TOO_MANY_LIBRARIES_SPECIFIED_ERROR
from ..biblib_exceptions import PermissionDeniedError


class OperationsView(BaseView):
    """
    Endpoint to conduct operations on a given library or set of libraries. Supported operations are
    union, intersection, difference, copy, and empty.
    """
    decorators = [advertise('scopes', 'rate_limit')]
    scopes = ['user']
    rate_limit = [1000, 60 * 60 * 24]

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
                if isinstance(lib, basestring):
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
        if isinstance(secondary_libid, basestring):
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
        library = self.helper_slug_to_uuid(library)

        user_editing_uid = \
            self.helper_absolute_uid_to_service_uid(absolute_uid=user_editing)

        # Check the permissions of the user
        if not self.write_access(service_uid=user_editing_uid,
                                 library_id=library):
            return err(NO_PERMISSION_ERROR)

        try:
            data = get_post_data(
                request,
                types=dict(libraries=list, action=basestring, name=basestring, description=basestring, public=bool)
            )
        except TypeError as error:
            current_app.logger.error('Wrong type passed for POST: {0} [{1}]'
                                     .format(request.data, error))
            return err(WRONG_TYPE_ERROR)

        if data['action'] in ['union', 'intersection', 'difference']:
            if 'libraries' not in data:
                return err(NO_LIBRARY_SPECIFIED_ERROR)
            if 'name' not in data:
                data['name'] = 'Untitled {0}.'.format(get_date.isoformat())
            if 'public' not in data:
                data['public'] = False

        if data['action'] == 'union':
            bib_union = self.setops_libraries(
                library_id=library,
                document_data=data,
                operation='union'
            )
            current_app.logger.info('Successfully took the union of {0} with {1}'
                    .format(library, data['libraries']))

            data['bibcode'] = bib_union
            if 'description' not in data:
                data['description'] = 'Union of {0} with {1}'.format(library, data['libraries'])

            library_dict = self.create_library(service_uid=user_editing_uid, library_data=data)

            return library_dict, 200

        elif data['action'] == 'intersection':
            bib_intersect = self.setops_libraries(
                library_id=library,
                document_data=data,
                operation='intersection'
            )
            current_app.logger.info('Successfully took the intersection of {0} with {1}'
                                    .format(library, data['libraries']))

            data['bibcode'] = bib_intersect
            if 'description' not in data:
                data['description'] = 'Intersection of {0} with {1}'.format(library, data['libraries'])

            library_dict = self.create_library(service_uid=user_editing_uid, library_data=data)
            return library_dict, 200

        elif data['action'] == 'difference':
            bib_diff = self.setops_libraries(
                library_id=library,
                document_data=data,
                operation='difference'
            )
            current_app.logger.info('Successfully took the difference of {0} - (minus) {1}'
                                    .format(library, data['libraries']))

            data['bibcode'] = bib_diff
            if 'description' not in data:
                data['description'] = 'Records that are in {0} but not in {1}'.format(library, data['libraries'])

            library_dict = self.create_library(service_uid=user_editing_uid, library_data=data)
            return library_dict, 200

        elif data['action'] == 'copy':
            if 'libraries' not in data:
                return err(NO_LIBRARY_SPECIFIED_ERROR)
            if len(data['libraries']) > 1:
                return err(TOO_MANY_LIBRARIES_SPECIFIED_ERROR)

            library_dict = self.copy_library(
                library_id=library,
                document_data=data
            )
            current_app.logger.info('Successfully copied {0} into {1}'
                                    .format(library, data['libraries']))

            with current_app.session_scope() as session:
                libid = self.helper_slug_to_uuid(data['libraries'][0])
                library = session.query(Library).filter_by(id=libid).one()
                bib = library.get_bibcodes()

                library_dict['bibcode'] = bib

            return library_dict, 200

        elif data['action'] == 'empty':
            library_dict = self.empty_library(
                library_id=library
            )
            current_app.logger.info('Successfully emptied {0} of all records'
                                    .format(library))

            with current_app.session_scope() as session:
                library = session.query(Library).filter_by(id=library).one()
                bib = library.get_bibcodes()

                library_dict['bibcode'] = bib

            return library_dict, 200

        else:
            current_app.logger.info('User requested a non-standard operation')
            return {}, 400