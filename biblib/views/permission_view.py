"""
Perimssion view
"""

from flask import request, current_app
from flask.ext.discoverer import advertise
from ..models import db, User, Library, Permissions
from ..client import client
from .base_view import BaseView
from sqlalchemy.orm.exc import NoResultFound
from ..utils import get_post_data, err
from http_errors import MISSING_USERNAME_ERROR, NO_PERMISSION_ERROR, \
    WRONG_TYPE_ERROR, API_MISSING_USER_EMAIL
from ..biblib_exceptions import PermissionDeniedError

class PermissionView(BaseView):
    """
    End point to manipulate the permissions between a user and a library
    """
    # TODO: Users that do not have an account, cannot be added to permissions
    # TODO:   - send invitation?

    decorators = [advertise('scopes', 'rate_limit')]
    scopes = ['user']
    rate_limit = [1000, 60*60*24]

    # Some permissions for this View
    read_permission = ['admin', 'owner']

    @staticmethod
    def has_permission(service_uid_editor,
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

    @staticmethod
    def add_permission(service_uid, library_id, permission, value):
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

            # Check if all permissions are False, then remove completely
            if not (new_permission.read |
                    new_permission.write |
                    new_permission.admin |
                    new_permission.owner):

                current_app.logger.info('Deleting permissions for {0} and '
                                        'library {1} as all permissions are '
                                        'False. {2}'
                                        .format(service_uid,
                                                library_id,
                                                new_permission))

                db.session.delete(new_permission)
            else:
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

    @staticmethod
    def api_uid_email_lookup(user_info):
        """
        Queries the API service that converts uid to email or email to uid,
        dependent upon the type passed by the user
        :param user_info: <int> is userID, and <unicode>/<str> is email

        :return: the API userID or API e-mail
        """

        if isinstance(user_info, int):

            service = '{api}/{uid}'.format(
                api=current_app.config['BIBLIB_USER_EMAIL_ADSWS_API_URL'],
                uid=user_info
            )
            current_app.logger.info('Obtaining e-mail of user: {0} [API UID]'
                                    .format(user_info))

            response = client().get(
                service
            )

            return response.json()['email']
        else:
            return None

    @classmethod
    def get_permissions(cls, library_id):
        """
        Looks up and returns the permissions for all of the users that have
        any permissions.
        :param library_id: the library ID to look up permissions

        :return: list of dictionaries containing the user email and permission
        """

        # Find the permissions for the library
        result = db.session.query(Permissions, User)\
            .join(Permissions.user)\
            .filter(Permissions.library_id == library_id)\
            .all()

        # Formulate the return content
        permission_list = []

        for permission, user in result:

            # Convert the user id into
            user = cls.api_uid_email_lookup(user_info=user.absolute_uid)

            all_permissions = filter(
                lambda key: permission.__dict__[key],
                ['read', 'write', 'admin', 'owner']
            )

            permission_list.append(
                {user: all_permissions}
            )

        return permission_list

    @classmethod
    def read_access(cls, service_uid, library_id):
        """
        Checks if the user has access to read the permissions on a given
        library
        :param service_uid: the user ID within this microservice
        :param library_id: the library ID to look up permissions

        :return: has access (True), does not have access (False)
        """

        for access_type in cls.read_permission:
            if BaseView.helper_access_allowed(service_uid=service_uid,
                                              library_id=library_id,
                                              access_type=access_type):
                return True

        return False

    # Methods
    def get(self, library):
        """
        HTTP GET request that returns the permissions for a given library
        :param library: library ID

        :return: list of permissions

        Header:
        -------
        Must contain the API forwarded user ID of the user accessing the end
        point

        Return data:
        ------------
        JSON with a list containing dictionary elements
        [{<user-email>: [<permission1>, ...., <permissionN>]},
        ...., {<user-email>: [<permission>1, ...., <permissionN>]}]

        Permissions:
        -----------
        The following type of user can access permission:
          - owner
          - admin
        """
        # Get the user requesting this from the header
        try:
            user_api = self.helper_get_user_id()
        except KeyError:
            return err(MISSING_USERNAME_ERROR)

        # URL safe base64 string to UUID
        library = self.helper_slug_to_uuid(library)

        # Get the service ID from the API resolver
        service_uid = \
            self.helper_absolute_uid_to_service_uid(absolute_uid=user_api)

        # Check permissions
        if not self.read_access(service_uid=service_uid,
                                library_id=library):
            current_app.logger.error(
                'User {0} has the wrong permissions to get the '
                'permission list for library {1}'
                .format(service_uid, library)
            )
            return err(NO_PERMISSION_ERROR)

        # Get permissions
        permissions = self.get_permissions(library_id=library)

        # Return data
        return permissions, 200

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

        Return data:
        -----------
        No data

        Permissions:
        -----------
        The following type of user can update a permission:
          - owner
          - admin

        Notes:
        Currently, the posts are per user, per permission. If its wanted that
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

        try:
            permission_data = get_post_data(
                request,
                types=dict(
                    email=unicode,
                    permission=unicode,
                    value=bool
                )
            )
        except TypeError as error:
            current_app.logger.error('Wrong type passed for POST: {0} [{1}]'
                                     .format(request.data, error))
            return err(WRONG_TYPE_ERROR)

        current_app.logger.info('Requested permission changes for user {0}:'
                                ' {1} for library {2}, by user: {3}'
                                .format(permission_data['email'],
                                        permission_data,
                                        library,
                                        user_editing_uid)
                                )

        try:
            secondary_user = self.helper_email_to_api_uid(permission_data)
            current_app.logger.info('User: {0} corresponds to: {1}'
                                    .format(permission_data['email'],
                                            secondary_user))
        except NoResultFound:
            return err(API_MISSING_USER_EMAIL)

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
            return err(NO_PERMISSION_ERROR)

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
            return err(NO_PERMISSION_ERROR)

        current_app.logger.info('...SUCCESS.')
        return {}, 200
