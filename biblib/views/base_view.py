"""
Base view
"""
import uuid
import base64

from ..views import DEFAULT_LIBRARY_NAME_PREFIX, DEFAULT_LIBRARY_DESCRIPTION, \
    USER_ID_KEYWORD
from flask import request, current_app
from flask.ext.restful import Resource
from ..models import db, User, Library, Permissions
from ..client import client
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from ..biblib_exceptions import BackendIntegrityError, PermissionDeniedError

class BaseView(Resource):
    """
    A base view class to keep a single version of common functions used between
    all of the views.
    """

    @staticmethod
    def helper_uuid_to_slug(library_uuid):
        """
        Convert a UUID to a slug

        See a discussion about the details here:
        http://stackoverflow.com/questions/12270852/
        convert-uuid-32-character-hex-string-into-a-
        youtube-style-short-id-and-back
        :param library_uuid: unique identifier for the library

        :return: library_slug: base64 URL safe slug
        """
        library_slug = base64.urlsafe_b64encode(library_uuid.bytes)
        library_slug = library_slug.rstrip('=\n').replace('/', '_')
        current_app.logger.info('Converted uuid: {0} to slug: {1}'
                                .format(library_uuid, library_slug))
        return library_slug

    @staticmethod
    def helper_slug_to_uuid(library_slug):
        """
        Convert a slug to a UUID

        See a discussion about the details here:
        http://stackoverflow.com/questions/12270852/
        convert-uuid-32-character-hex-string-into-a-
        youtube-style-short-id-and-back

        Keep in mind that base64 only works on bytes, and so they have to be
        encoded in ASCII. Flask uses unicode, and so you must modify the
         encoding before passing it to base64. This is fine, given we output
         all our encoded URLs for libraries as strings encoded in ASCII and do
         not accept any unicode characters.

        :param library_slug: base64 URL safe slug

        :return: library_uuid: unique identifier for the library
        """

        library_uuid = (library_slug + '==').replace('_', '/')
        library_uuid = library_uuid.encode('ascii')
        library_uuid = uuid.UUID(bytes=base64.urlsafe_b64decode(library_uuid))
        current_app.logger.info('Converted slug: {0} to uuid: {1}'
                                .format(library_slug, library_uuid))
        return str(library_uuid)

    @staticmethod
    def helper_get_user_id():
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

    @staticmethod
    def helper_create_user(absolute_uid):
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

    @staticmethod
    def helper_user_exists(absolute_uid):
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

    @staticmethod
    def helper_absolute_uid_to_service_uid(absolute_uid):
        """
        Convert the API UID to the BibLib service ID.

        If the user does not exist in the database, first create a user.

        :param absolute_uid: API UID
        :return: BibLib service ID
        """

        if not BaseView.helper_user_exists(absolute_uid=absolute_uid):
            user = BaseView.helper_create_user(absolute_uid=absolute_uid)
        else:
            user = User.query.filter(User.absolute_uid == absolute_uid).one()
        current_app.logger.info('User found: {0} -> {1}'
                                .format(absolute_uid, user.id))

        return user.id

    @staticmethod
    def helper_email_to_api_uid(permission_data):
        """
        A proxy to the user/e-mail resolver service. Passes on any errors from
        the API.

        :param permission_data: dictionary that should contain an e-mail key
        :return: int of the user id
        """
        try:
            service = '{api}/{email}'.format(
                api=current_app.config['BIBLIB_USER_EMAIL_ADSWS_API_URL'],
                email=permission_data['email']
            )
            current_app.logger.info('Obtaining UID of user: {0}'
                                    .format(permission_data['email']))
            response = client().get(
                service
            )
        except KeyError as error:
            current_app.logger.error('No user email provided. [{0}]'
                                     .format(error))
            raise

        if response.status_code == 200:
            return int(response.json()['id'])
        elif response.status_code == 404:
            raise NoResultFound('API does not have this user')
        else:
            raise Exception('Unknown internal error')

    @staticmethod
    def helper_access_allowed(service_uid, library_id, access_type):
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

    @staticmethod
    def helper_library_exists(library_id):
        """
        Helper function that checks if a library exists in the database or not
        by catching the raise and returning a True/False statement.
        :param library_id: the unique ID of the library

        :return: bool for exists (True) or does not (False)
        """
        try:
            Library.query.filter(Library.id == library_id).one()
            return True
        except NoResultFound:
            return False

    @staticmethod
    def helper_validate_library_data(service_uid, library_data):
        """
        Validates the library data to ensure the user does not give empty
        content for the title and description.

        :param service_uid: the user ID within this microservice
        :param library_data: content needed to create a library

        :return: validated name and description
        """

        _name = library_data.get('name') or DEFAULT_LIBRARY_NAME_PREFIX
        _description = library_data.get('description') or \
            DEFAULT_LIBRARY_DESCRIPTION

        current_app.logger.info('Creating library for user_service: {0:d}, '
                                'with properties: {1}'
                                .format(service_uid, library_data))

        # We want to ensure that the users have unique library names. However,
        # it should be possible that they have access to other libraries from
        # other people, that have the same name
        library_names = \
            [i.library.name for i in
             Permissions.query.filter(Permissions.user_id == service_uid,
                                      Permissions.owner == True).all()]

        matches = [name for name in library_names if name == _name]
        if matches:
            current_app.logger.error('Name supplied for the library already '
                                     'exists: "{0}" ["{1}"]'.format(_name,
                                                                    matches))
            raise BackendIntegrityError('Library name already exists.')

        if _name == DEFAULT_LIBRARY_NAME_PREFIX:
            default_names = [lib_name for lib_name
                             in library_names
                             if DEFAULT_LIBRARY_NAME_PREFIX
                             in lib_name]

            _extension = len(default_names) + 1
            _name = '{0} {1}'.format(_name,
                                     _extension)

        library_out = {}
        for key in library_data:
            library_out[key] = library_data[key]
        library_out['name'] = _name
        library_out['description'] = _description

        return library_out
