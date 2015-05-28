"""
Views
"""

__author__ = 'J. Elliott'
__maintainer__ = 'J. Elliott'
__copyright__ = 'ADS Copyright 2015'
__version__ = '1.0'
__email__ = 'ads@cfa.harvard.edu'
__status__ = 'Production'
__credit__ = ['V. Sudilovsky']
__license__ = 'MIT'

from flask import request, current_app
from flask.ext.restful import Resource
from flask.ext.discoverer import advertise
from models import db, User, Library, Permissions
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from utils import get_post_data, BackendIntegrityError, PermissionDeniedError

DUPLICATE_LIBRARY_NAME_ERROR = {'body': 'Library name given already '
                                        'exists and must be unique.',
                                'number': 409}

MISSING_LIBRARY_ERROR = {'body': 'Library specified does not exist.',
                         'number': 410}


MISSING_DOCUMENT_ERROR = {'body': 'Document specified does not exist.',
                          'number': 410}

MISSING_USERNAME_ERROR = {'body': 'You did not supply enough user details',
                          'number': 400}

NO_PERMISSION_ERROR = {'body': 'You do not have the correct permissions or'
                               'this library does not exist.',
                       'number': 403}

USER_ID_KEYWORD = 'X-Adsws-Uid'


class BaseView(Resource):
    """
    A base view class to keep a single version of common functions used between
    all of the views.
    """

    def helper_get_user_id(self):
        """
        Helper function: get the user id from the header, otherwise raise
        a key error exception

        :return: unique API user ID
        """
        try:
            user = request.headers[USER_ID_KEYWORD]
            if user.isdigit():
                user = int(user)
            return user
        except KeyError:
            current_app.logger.error('No username passed')
            raise

    def helper_create_user(self, absolute_uid):
        """
        Creates a user in the database with a UID from the API
        :param absolute_uid: UID from the API

        :return: SQLAlchemy User instance
        """

        try:
            user = User(absolute_uid=absolute_uid)
            db.session.add(user)
            db.session.commit()

            current_app.logger.info('Successfully created user: {0} [API] as '
                                    '{1} [Microservice]'
                                    .format(absolute_uid, user.id))
            return user

        except IntegrityError as error:
            current_app.logger.error('IntegrityError. User: {0:d} was not'
                                     'added. Full traceback: {1}'
                                     .format(absolute_uid, error))
            raise

    def helper_user_exists(self, absolute_uid):
        """
        Checks if a use exists before it would attempt to create one

        :param absolute_uid: UID from the API
        :return: boolean for if the user exists
        """

        user_count = User.query.filter(User.absolute_uid == absolute_uid).all()
        user_count = len(user_count)
        if user_count == 1:
            current_app.logger.info('User exists in database: {0} [API]'
                                    .format(absolute_uid))
            return True
        elif user_count == 0:
            current_app.logger.warning('User does not exist in database: {0} '
                                       '[API]'.format(absolute_uid))
            return False

    def helper_absolute_uid_to_service_uid(self, absolute_uid):
        """
        Convert the API UID to the BibLib service ID.

        If the user does not exist in the database, first create a user.

        :param absolute_uid: API UID
        :return: BibLib service ID
        """

        if not self.helper_user_exists(absolute_uid=absolute_uid):
            user = self.helper_create_user(absolute_uid=absolute_uid)
        else:
            user = User.query.filter(User.absolute_uid == absolute_uid).one()
        current_app.logger.info('User found: {0} -> {1}'
                                .format(absolute_uid, user.id))

        return user.id

    def helper_email_to_api_uid(self, permission_data):
        # XXX: The user does not exist (404 returned)
        # XXX: The api timesout on response
        # XXX: general errors from the API (400)
        try:
            service = '{api}/{email}'.format(
                api=current_app.config['USER_EMAIL_ADSWS_API_URL'],
                email=permission_data['email']
            )
            response = current_app.config['BIBLIB_CLIENT'].session.get(
                service
            )
        except KeyError as error:
            current_app.logger.error('No user email provided.')
            return {'error': MISSING_USERNAME_ERROR['body']}, \
                MISSING_USERNAME_ERROR['number']

        if response.status_code == 200:
            return int(response.json()['uid'])

    def helper_access_allowed(self, service_uid, library_id, access_type):
        """
        Determines if the given user has permissions to look at the content
        of a library.

        :param service_uid: the user ID within this microservice
        :param library_id: the unique ID of the library
        :param access_type: list of access types to check

        :return: boolean, access (True), no access (False)
        """

        try:
            permissions = Permissions.query.filter(
                Permissions.library_id == library_id,
                Permissions.user_id == service_uid
            ).one()

            return getattr(permissions, access_type)

        except NoResultFound as error:
            current_app.logger.error('No permissions for '
                                     'user: {0}, library: {1}, permission: {2}'
                                     ' [{3}]'.format(service_uid, library_id,
                                                     access_type, error))
            return False



class UserView(BaseView):
    """
    End point to create a library for a given user

    XXX: need to ignore the anon user, they should not be able to create libs
    XXX: public/private
    XXX: name of the library already exists
    XXX: must give the library name/missing input function saves time
    """

    decorators = [advertise('scopes', 'rate_limit')]
    scopes = ['scope1', 'scope2']
    rate_limit = [1000, 60*60*24]

    def create_user(self, absolute_uid):
        """
        Creates a user in the database with a UID from the API
        :param absolute_uid: UID from the API

        :return: no return
        """

        try:
            user = User(absolute_uid=absolute_uid)
            db.session.add(user)
            db.session.commit()

        except IntegrityError as error:
            current_app.logger.error('IntegrityError. User: {0:d} was not'
                                     'added. Full traceback: {1}'
                                     .format(absolute_uid, error))
            raise

    def create_library(self, service_uid, library_data):
        """
        Creates a library for a user

        :param service_uid: the user ID within this microservice
        :param library_data: content needed to create a library

        :return: no return
        """

        _name = library_data['name']
        _description = library_data['description']
        _read = library_data['read']
        _write = library_data['write']
        _public = library_data['public']
        _owner = True

        current_app.logger.info('Creating library for user_service: {0:d}'
                                .format(service_uid))

        # We want to ensure that the users have unique library names. However,
        # it should be possible that they have access to other libraries from
        # other people, that have the same name
        library_names = \
            [i.library.name for i in
             Permissions.query.filter(Permissions.user_id == service_uid,
                                      Permissions.owner == True).all()]

        if _name in library_names:
            current_app.logger.error('Name supplied for the library already '
                                     'exists: "{0}"'.format(_name))
            raise BackendIntegrityError('Library name already exists.')

        try:

            # Make the library in the library table
            library = Library(name=_name,
                              description=_description,
                              public=_public)
            user = User.query.filter(User.id == service_uid).one()

            # Make the permissions
            permission = Permissions(
                read=_read,
                write=_write,
                owner=_owner,
            )

            # Use the ORM to link the permissions to the library and user,
            # so that no commit is required until the complete action is
            # finished. This means any rollback will not leave a single
            # library without permissions
            library.permissions.append(permission)
            user.permissions.append(permission)

            db.session.add_all([library, permission, user])
            db.session.commit()

            current_app.logger.info('Library: "{0}" made, user_service: {1:d}'
                                    .format(library.name, user.id))

            return library

        except IntegrityError as error:
            # Roll back the changes
            db.session.rollback()
            current_app.logger.error('IntegitryError, database has been rolled'
                                     'back. Caused by user_service: {0:d}.'
                                     'Full error: {1}'
                                     .format(user.id, error))
            # Log here
            raise
        except Exception:
            db.session.rollback()
            raise

    def get_libraries(self, absolute_uid):
        """
        Get all the libraries a user has
        :param absolute_uid: api UID of the user

        :return: list of libraries in json format
        """
        user_libraries = \
            Library.query.filter(User.absolute_uid == absolute_uid).all()

        output_libraries = []
        for library in user_libraries:
            payload = {
                'name': library.name,
                'id': '{0}'.format(library.id),
                'description': library.description,
            }
            output_libraries.append(payload)

        return output_libraries

    # Methods
    def get(self):
        """
        HTTP GET request that returns all the libraries that belong to a given
        user

        :param user: user ID as given by the API
        :return: list of the users libraries with the relevant information

        Header:
        Must contain the API forwarded user ID of the user accessing the end
        point

        Post body:
        ----------
        No post content accepted.

        XXX: Check that user is not anon
        """

        # Check that they pass a user id
        try:
            user = int(request.headers[USER_ID_KEYWORD])
        except KeyError:
            current_app.logger.error('No username passed')
            return {'error': MISSING_USERNAME_ERROR['body']}, \
                MISSING_USERNAME_ERROR['number']

        user_libraries = self.get_libraries(absolute_uid=user)
        return {'libraries': user_libraries}, 200

    def post(self):
        """
        HTTP POST request that creates a library for a given user

        :return: the response for if the library was successfully created

        Header:
        -------
        Must contain the API forwarded user ID of the user accessing the end
        point


        Post body:
        ----------
        KEYWORD, VALUE
        name:        <string>    name of the library (must be unique for that
                                 user)
        description: <string>    description of the library
        public:      <boolean>   is the library public to view
        """

        # Check that they pass a user id
        try:
            user = int(request.headers[USER_ID_KEYWORD])
        except KeyError:
            current_app.logger.error('No username passed')
            return {'error': MISSING_USERNAME_ERROR['body']}, \
                MISSING_USERNAME_ERROR['number']

        # Check if the user exists, if not, generate a user in the database
        current_app.logger.info('Checking if the user exists')
        if not self.helper_user_exists(absolute_uid=user):
            current_app.logger.info('User: {0:d}, does not exist.'
                                    .format(user))

            self.create_user(absolute_uid=user)
            current_app.logger.info('User: {0:d}, created.'.format(user))
        else:
            current_app.logger.info('User already exists.')

        # Switch to the service UID and not the API UID
        service_uid = self.helper_absolute_uid_to_service_uid(absolute_uid=user)
        current_app.logger.info('user_API: {0:d} is now user_service: {1:d}'
                                .format(user, service_uid))

        # Create the library
        data = get_post_data(request)
        try:
            library = \
                self.create_library(service_uid=service_uid, library_data=data)
        except BackendIntegrityError as error:
            return {'error': DUPLICATE_LIBRARY_NAME_ERROR['body']}, \
                DUPLICATE_LIBRARY_NAME_ERROR['number']

        return {'name': library.name,
                'id': '{0}'.format(library.id),
                'description': library.description}, 200


class LibraryView(BaseView):
    """
    End point to interact with a specific library, only returns library content
    if the user has the correct privileges.

    The GET requests are separate from the POST, DELETE requests as this class
    must be scopeless, whereas the others will have scope.

    XXX: need to ignore the anon user, they should not be able to do anything
    XXX: document already exists (only add a bibcode once)
    XXX: adding tags using PUT for RESTful endpoint?
    XXX: public/private behaviour

    """

    decorators = [advertise('scopes', 'rate_limit')]
    scopes = []
    rate_limit = [1000, 60*60*24]

    def get_documents_from_library(self, library_id):
        """
        Retrieve all the documents that are within the library specified
        :param library_id: the unique ID of the library

        :return: bibcodes
        """

        library = Library.query.filter(Library.id == library_id).one()
        return library

    def read_access(self, service_uid, library_id):
        """
        Defines which type of user has read permissions to a library.

        :param service_uid: the user ID within this microservice
        :param library_id: the unique ID of the library

        :return: boolean, access (True), no access (False)
        """

        read_allowed = ['read', 'write', 'admin', 'owner']
        for access_type in read_allowed:
            if self.helper_access_allowed(service_uid=service_uid,
                                   library_id=library_id,
                                   access_type=access_type):
                return True

        return False

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

        XXX: Needs authentification still
        """
        try:
            user = int(request.headers[USER_ID_KEYWORD])
        except KeyError:
            current_app.logger.error('No username passed')
            return {'error': MISSING_USERNAME_ERROR['body']}, \
                MISSING_USERNAME_ERROR['number']

        current_app.logger.info('User: {0} requested library: {1}'
                                .format(user, library))

        # If the library is public, allow access
        try:
            library = self.get_documents_from_library(library_id=library)
            documents = library.bibcode
            if library.public:
                current_app.logger.info('Library: {0} is public'
                                        .format(library.id))
                return {'documents': documents}, 200

        except:
            return {'error': MISSING_LIBRARY_ERROR['body']}, \
                MISSING_LIBRARY_ERROR['number']

        # If the user does not exist then there are no associated permissions
        # If the user exists, they will have permissions
        if self.helper_user_exists(absolute_uid=user):
            service_uid = \
                self.helper_absolute_uid_to_service_uid(absolute_uid=user)
        else:
            current_app.logger.error('User:{0} does not exist in the database.'
                                     ' Therefore will not have extra '
                                     'privileges to view the library: {1}'
                                     .format(user, library.id))

            return {'error': NO_PERMISSION_ERROR['body']}, \
                NO_PERMISSION_ERROR['number']

        # If they do not have access, exit
        if not self.read_access(service_uid=service_uid, library_id=library.id):
            current_app.logger.error(
                'User: {0} does not have access to library: {1}. DENIED'
                .format(service_uid, library.id)
            )
            return {'error': NO_PERMISSION_ERROR['body']}, \
                NO_PERMISSION_ERROR['number']

        # If they have access, let them obtain the requested content
        current_app.logger.info('User: {0} has access to library: {1}. '
                                'ALLOWED'
                                .format(user, library.id))

        return {'documents': documents}, 200


class DocumentView(BaseView):
    """
    End point to interact with a specific library, by adding documents and
    removing documents. You also use this endpoint to delete the entire
    library as this method should be scoped.

    XXX: need to ignore the anon user, they should not be able to do anything
    XXX: document already exists (only add a bibcode once)
    XXX: adding tags using PUT for RESTful endpoint?
    XXX: public/private behaviour

    """

    decorators = [advertise('scopes', 'rate_limit')]
    scopes = ['scope1', 'scope2']
    rate_limit = [1000, 60*60*24]

    def add_document_to_library(self, library_id, document_data):
        """
        Adds a document to a user's library
        :param library_id: the library id to update
        :param document_data: the meta data of the document

        :return: no return
        """

        current_app.logger.info('Adding a document: {0} to library_uuid: {1}'
                                .format(document_data, library_id))
        # Find the specified library
        library = Library.query.filter(Library.id == library_id).one()
        if not library.bibcode:
            current_app.logger.debug('Zero length array: {0}'
                                     .format(library.bibcode))
            library.bibcode = [document_data['bibcode']]
        else:
            current_app.logger.debug('Non-Zero length array: {0}'
                                     .format(library.bibcode))
            library.bibcode.append(document_data['bibcode'])

        db.session.commit()

        current_app.logger.info(library.bibcode)

    def remove_documents_from_library(self, library_id, document_data):
        """
        Remove a given document from a specific library

        :param library_id: the unique ID of the library
        :param document_data: the meta data of the document

        :return: no return
        """
        current_app.logger.info('Removing a document: {0} from library_uuid: '
                                '{1}'.format(document_data, library_id))
        library = Library.query.filter(Library.id == library_id).one()
        library.bibcode.remove(document_data['bibcode'])
        db.session.commit()
        current_app.logger.info('Removed document successfully: {0}'
                                .format(library.bibcode))

    def delete_library(self, library_id):
        """
        Delete the entire library from the database
        :param library_id: the unique ID of the library

        :return: no return
        """

        library = Library.query.filter(Library.id == library_id).one()
        db.session.delete(library)
        db.session.commit()

    def write_access(self, service_uid, library_id):
        """
        Defines which type of user has write permissions to a library.

        :param service_uid: the user ID within this microservice
        :param library_id: the unique ID of the library

        :return: boolean, access (True), no access (False)
        """

        read_allowed = ['write', 'admin', 'owner']
        for access_type in read_allowed:
            if self.helper_access_allowed(service_uid=service_uid,
                                   library_id=library_id,
                                   access_type=access_type):
                return True

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

        bibcode:  <string>        Bibcode to be added
        action:   add, remove     add - adds a bibcode, remove - removes a
                                  bibcode

        Notes:
        Currently, bibcodes are just strings. If lists are required, then open
        an issue on the repository.

        XXX: Needs authentification still
        XXX: Want a tidier try/except/return pattern
        """

        # Get the user requesting this from the header
        try:
            user_editing = self.helper_get_user_id()
        except KeyError:
            return {'error': MISSING_USERNAME_ERROR['body']}, \
                MISSING_USERNAME_ERROR['number']

        user_editing_uid = \
            self.helper_absolute_uid_to_service_uid(absolute_uid=user_editing)

        # Check the permissions of the user
        if not self.write_access(service_uid=user_editing_uid,
                                 library_id=library):
            return {'error': NO_PERMISSION_ERROR['body']}, \
                   NO_PERMISSION_ERROR['number']

        data = get_post_data(request)
        if data['action'] == 'add':
            current_app.logger.info('User requested to add a document')
            self.add_document_to_library(library_id=library,
                                         document_data=data)
            return {}, 200

        elif data['action'] == 'remove':
            current_app.logger.info('User requested to remove a document')
            self.remove_documents_from_library(
                library_id=library,
                document_data=data
            )
            return {}, 200

        else:
            current_app.logger.info('User requested a non-standard action')
            return {}, 400

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
        """

        try:
            user = int(request.headers[USER_ID_KEYWORD])
        except KeyError:
            current_app.logger.error('No username passed')
            return {'error': MISSING_USERNAME_ERROR['body']}, \
                MISSING_USERNAME_ERROR['number']

        try:
            current_app.logger.info('user_API: {0:d} '
                                    'requesting to delete library: {0}'
                                    .format(user, library))

            self.delete_library(library_id=library)
            current_app.logger.info('Deleted library.')

        except NoResultFound as error:
            current_app.logger.info('Failed to delete: {0}'.format(error))
            return {'error': MISSING_LIBRARY_ERROR['body']}, \
                MISSING_LIBRARY_ERROR['number']

        return {}, 200


class PermissionView(BaseView):
    """
    End point to manipulate the permissions between a user and a library


    XXX: Users that do not have an account, cannot be added to permissions
    XXX:   - send invitation?
    XXX:   - if they exist in the API database but have not created a library
             we still need to create a user entry in the database for them
    XXX: add read, write, admin
    XXX: remove read, write, admin
    XXX: only an admin/owner can add permissions to someone
    XXX: update permissions stub data (and stub data in general)
    XXX: pass user and permissions as lists
    """

    decorators = [advertise('scopes', 'rate_limit')]
    scopes = ['scope1', 'scope2']
    rate_limit = [1000, 60*60*24]

    def has_permission(self,
                       service_uid_editor,
                       service_uid_modify,
                       library_id):
        """
        Check if the user wanting to change the library has the correct
        permissions to do so, and the user to be changed is not the owner.
        :param service_uid_editor: the user ID of the editor
        :param service_uid_modify: the user ID of the user to be edited
        :param library_id: the library id

        :return: boolean
        """

        if service_uid_editor == service_uid_modify:
            current_app.logger.error('Editing user: {0} and user to edit: {1}'
                                     ' are the same. This is not allowed.'
                                     .format(service_uid_modify,
                                             service_uid_editor))
            return False

        current_app.logger.info('Checking if user: {0}, can edit the '
                                'permissions of user: {1}'
                                .format(
                                    service_uid_editor,
                                    service_uid_modify
                                ))

        # Check if the editor has permissions
        try:
            editor_permissions = Permissions.query.filter(
                Permissions.user_id == service_uid_editor,
                Permissions.library_id == library_id
            ).one()
        except NoResultFound as error:
            current_app.logger.error(
                'User: {0} has no permissions for this library: {1}'
                .format(service_uid_editor, error)
            )
            return False

        if editor_permissions.owner:
            current_app.logger.info('User: {0} is owner, so is allowed to '
                                    'change permissions'
                                    .format(service_uid_editor))
            return True

        # Check if the user to be modified has permissions
        try:
            modify_permissions = Permissions.query.filter(
                Permissions.user_id == service_uid_modify,
                Permissions.library_id == library_id
            ).one()
        except NoResultFound:
            modify_permissions = False

        # if the editor is admin, and the modifier has no permissions
        if editor_permissions.admin:

            # user to be modified has no permissions
            if not modify_permissions:
                return True

            # user to be modified is not owner
            if not modify_permissions.owner:
                return True
        else:
            return False

    def add_permission(self, service_uid, library_id, permission, value):
        """
        Adds a permission for a user to a specific library
        :param service_uid: the user ID within this microservice
        :param library_id: the library id to update
        :param permission: the permission to be added
        :param value: boolean that accompanies the permission

        :return: no return
        """

        if permission not in ['read', 'write', 'admin']:
            raise PermissionDeniedError('Permission Error')

        try:
            # If the user has permissions for this already
            new_permission = Permissions.query.filter(
                Permissions.user_id == service_uid,
                Permissions.library_id == library_id
            ).one()

            current_app.logger.info(
                'User: {0} has permissions already for '
                'library: {1}. Modifying: "{2}" from [{3}] '
                'to [{4}]'
                .format(service_uid,
                        library_id,
                        permission,
                        getattr(new_permission, permission),
                        value)
            )

            setattr(new_permission, permission, value)
            db.session.add(new_permission)

        except NoResultFound:
            # If no permissions set yet for user and library
            current_app.logger.info('No permissions yet set for user: {0} for '
                                    'library: {1}. Using defaults for setup'
                                    ' and allocating "{2}" to [{3}]'
                                    .format(service_uid,
                                            library_id,
                                            permission,
                                            value))

            user = User.query.filter(User.id == service_uid).one()
            library = Library.query.filter(Library.id == library_id).one()

            new_permission = Permissions(
                read=False,
                write=False,
                admin=False,
                owner=False,
            )

            setattr(new_permission, permission, value)

            user.permissions.append(new_permission)
            library.permissions.append(new_permission)
            db.session.add_all([user, library, new_permission])

        db.session.commit()

    # Methods
    def post(self, library):
        """
        HTTP POST request that modifies the permissions of a library
        :param library: library ID

        :return: the response for if the library was successfully created

        Header:
        -------
        Must contain the API forwarded user ID of the user accessing the end
        point

        Post data:
        ----------
        KEYWORD, VALUE
        email:   <e-mail@address>, specifies which user's permissions to be
                                   modified
        permission:  read, write,  specifies which permission to change
                     admin
        value:   boolean,          whether the user has this permission

        Notes:
        Currently, the posts are per user, per permission. If it wanted that
        lists can be passed, then open an issue. In my mind, it made more
        sense that you can retrieve the correct errors in a request/response
        cycle, rather than complicating the response with a mixture of success
        and failures.

        For example, if an admin tries to modify the access for a random person
        without permissions, and the owner, the admin is not allowed to modify
        the owner. This would be both a success 200, and a forbidden, 404, so
        I do not think that makes sense. However, if there are strong arguments
        for a list input and the backend handling it, then open an issue on the
        repository.

        XXX: Need a helper function to check the user gave the right input
        XXX: Need a check that there is the correct content passed
        XXX: Need to handle when there is no e-mail for the user as they do not
             exist in the API
        XXX: Need a get endpoint to find out what permissions people have as
             well
        XXX: input values should be type checked as well in a systematic way
        """

        # Get the user requesting this from the header
        try:
            user_editing = self.helper_get_user_id()
        except KeyError:
            return {'error': MISSING_USERNAME_ERROR['body']}, \
                MISSING_USERNAME_ERROR['number']

        user_editing_uid = \
            self.helper_absolute_uid_to_service_uid(absolute_uid=user_editing)

        permission_data = get_post_data(request)
        current_app.logger.info('Requested permission changes for user {0}:'
                                ' {1} for library {2}, by user: {3}'
                                .format(permission_data['email'],
                                        permission_data,
                                        library,
                                        user_editing_uid)
                                )

        secondary_user = self.helper_email_to_api_uid(permission_data)
        current_app.logger.info('User: {0} corresponds to: {1}'
                                .format(permission_data['email'],
                                        secondary_user))

        secondary_service_uid = \
            self.helper_absolute_uid_to_service_uid(
                absolute_uid=secondary_user)
        current_app.logger.info('User: {0} is internally: {1}'
                                .format(secondary_user, secondary_service_uid))

        current_app.logger.info('Modifying permissions STARTING....')

        if not self.has_permission(service_uid_editor=user_editing_uid,
                                   service_uid_modify=secondary_service_uid,
                                   library_id=library):

            current_app.logger.error(
                'User: {0} does not have permissions to edit: {1}'
                .format(user_editing_uid, library)
            )
            return {'error': NO_PERMISSION_ERROR['body']}, \
                NO_PERMISSION_ERROR['number']

        try:
            self.add_permission(service_uid=secondary_service_uid,
                                library_id=library,
                                permission=permission_data['permission'],
                                value=permission_data['value'])
        except PermissionDeniedError:
            current_app.logger.error('User: {0} does not have permissions to '
                                     'modify the value of: {1}'
                                     .format(user_editing_uid,
                                             permission_data['permission']))
            return {'error': NO_PERMISSION_ERROR['body']}, \
                    NO_PERMISSION_ERROR['number']

        current_app.logger.info('...SUCCESS.')
        return {}, 200