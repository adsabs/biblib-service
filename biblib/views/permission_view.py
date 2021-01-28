"""
Perimssion view
"""

from flask import request, current_app
from flask_discoverer import advertise
from ..models import User, Library, Permissions
from ..client import client
from .base_view import BaseView
from sqlalchemy.orm.exc import NoResultFound
from ..utils import get_post_data, err
from .http_errors import MISSING_USERNAME_ERROR, NO_PERMISSION_ERROR, \
    WRONG_TYPE_ERROR, API_MISSING_USER_EMAIL, BAD_LIBRARY_ID_ERROR
from ..biblib_exceptions import PermissionDeniedError
from ..emails import PermissionsChangedEmail
from jinja2 import Environment, PackageLoader, select_autoescape

env = Environment(
    loader=PackageLoader('biblib', 'templates'),
    autoescape=select_autoescape(enabled_extensions=('html', 'xml'),
                                 default_for_string=True)
)

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
        with current_app.session_scope() as session:
            try:
                editor_permissions = session.query(Permissions).filter(
                    Permissions.user_id == service_uid_editor,
                    Permissions.library_id == library_id
                ).one()
            except NoResultFound as error:
                current_app.logger.error(
                    'User: {0} has no permissions for this library: {1}'
                    .format(service_uid_editor, error)
                )
                return False

            if editor_permissions.permissions['owner']:
                current_app.logger.info('User: {0} is owner, so is allowed to '
                                        'change permissions'
                                        .format(service_uid_editor))
                return True

            # Check if the user to be modified has permissions
            try:
                modify_permissions = session.query(Permissions).filter(
                    Permissions.user_id == service_uid_modify,
                    Permissions.library_id == library_id
                ).one()
            except NoResultFound:
                modify_permissions = False

            # if the editor is admin, and the modifier has no permissions
            if editor_permissions.permissions['admin']:

                # user to be modified has no permissions
                if not modify_permissions:
                    return True

                # user to be modified is not owner
                if not modify_permissions.permissions['owner']:
                    return True

                # otherwise the user to be modified is the owner, so not allowed
                return False
            else:
                return False

    @staticmethod
    def add_permission(service_uid, library_id, permission):
        """
        Adds a permission for a user to a specific library
        :param service_uid: the user ID within this microservice
        :param library_id: the library id to update
        :param permission: dict of the permissions to be added/modified

        :return: no return
        """

        to_set = [k for k,v in permission.iteritems() if (type(v) == bool)]
        if not set(to_set).issubset(set(['read', 'write', 'admin', 'owner'])):
            raise PermissionDeniedError('Permission Error')

        with current_app.session_scope() as session:
            try:
                # If the user has permission for this already
                new_permission = session.query(Permissions).filter_by(
                    user_id = service_uid,
                    library_id = library_id
                ).one()

                # can't change owner permission this way - must go through TransferView
                if permission.get('owner') and \
                        (getattr(new_permission, 'permissions').get('owner',False) != permission['owner']):
                    raise PermissionDeniedError('Permission Error')

                current_app.logger.info(
                    'User: {0} has permission already for '
                    'library: {1}. Modifying: "{2}" from [{3}] '
                    'to [{4}]'
                    .format(service_uid,
                            library_id,
                            permission.keys(),
                            getattr(new_permission, 'permissions'),
                            permission.values())
                )

                for p, value in permission.iteritems():
                    getattr(new_permission, 'permissions')[p] = value

                # Check if all permission are False, then remove completely
                if not (new_permission.permissions['read'] |
                        new_permission.permissions['write'] |
                        new_permission.permissions['admin'] |
                        new_permission.permissions['owner']):

                    current_app.logger.info('Deleting permission for {0} and '
                                            'library {1} as all permission are '
                                            'False. {2}'
                                            .format(service_uid,
                                                    library_id,
                                                    new_permission))

                    session.delete(new_permission)
                else:
                    session.add(new_permission)

            except NoResultFound:
                # If no permission set yet for user and library
                current_app.logger.info('No permission yet set for user: {0} for '
                                        'library: {1}. Using defaults for setup'
                                        ' and allocating "{2}"'
                                        .format(service_uid,
                                                library_id,
                                                permission))

                user = session.query(User).filter_by(id = service_uid).one()
                library = session.query(Library).filter_by(id = library_id).one()

                new_permission = Permissions(permissions = {'read': False,
                                                            'write': False,
                                                            'admin': False,
                                                            'owner': False})

                # can't set owner permission this way
                if permission.get('owner',False) is not False:
                    raise PermissionDeniedError('Permission Error')

                for p, value in permission.iteritems():
                    getattr(new_permission, 'permissions')[p] = value

                # Check if all permission are False, then remove completely
                if not (new_permission.permissions['read'] |
                        new_permission.permissions['write'] |
                        new_permission.permissions['admin'] |
                        new_permission.permissions['owner']):
                    
                    current_app.logger.info('Not adding permissions for {0} and '
                                            'library {1} as all permission are '
                                            'False. {2}'
                                            .format(service_uid,
                                                    library_id,
                                                    new_permission))
                else:     
                    user.permissions.append(new_permission)
                    library.permissions.append(new_permission)
                    session.add_all([user, library, new_permission])

            session.commit()

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

        with current_app.session_scope() as session:
            # Find the permissions for the library
            result = session.query(Permissions, User)\
                .join(Permissions.user)\
                .filter(Permissions.library_id == library_id)\
                .all()

            # Formulate the return content
            permission_list = []

            for permission, user in result:

                # Convert the user id into
                user = cls.api_uid_email_lookup(user_info=user.absolute_uid)

                all_permissions = filter(
                    lambda key: permission.permissions[key],
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

    @staticmethod
    def format_permission_payload(library_name, library_id, permission_data):
        """
        Format the permission info into plain text and HTML payloads for the email

        :param library_name: string; name of library
        :param library_id: string; URL-safe version of library ID, used to create link to library
        :param permission_data: dict; keys:
                                    permission_data: dict w/ permissions (keys) and Boolean values
                                    email: email address of user receiving email
        :return: payload_plain, payload_html
        """

        email = permission_data.get('email', None)
        permissions = permission_data.get('permission', None)

        if not email or not permissions:
            current_app.logger.error('Must pass email and permissions in permission data. '
                                     'Library ID: {0}, permission data: {1}'.format(library_id, permission_data))
            raise RuntimeError('Insufficient permission data passed')

        readable_permissions = {'read': 'read only',
                                'write': 'read and write only',
                                'admin': 'admin (includes read and write)',
                                'owner': 'owner'}

        payload_plain_info = []
        payload_html_info = {}
        for p, value in permissions.iteritems():
            readable_permission = readable_permissions.get(p, None)
            if readable_permission:
                tmp = u'Library: {0} (ID: {1}) \n    Permission: {2} \n    Have permission? {3} \n'.\
                    format(library_name, library_id, readable_permission, value)
                payload_html_info[readable_permission] = value
            else:
                current_app.logger.error('Permission {0} not allowed; part of payload {1}. Exiting.'.format(p, permission_data))
                raise ValueError('Wrong permission type passed')

            payload_plain_info.append(tmp)

        payload_plain = '''
            Hi,
            Another user has recently updated your library permissions for the following libraries: 

            {payload}

            If this is a mistake, please contact ADS Help (adshelp@cfa.harvard.edu). 

            - the ADS team
            '''.format(payload='\n    '.join(payload_plain_info))

        template = env.get_template('permission_email.html')
        payload_html = template.render(email_address=email,
                                       payload=payload_html_info,
                                       lib_name=library_name,
                                       lib_id=library_id)

        return payload_plain, payload_html

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
        try:
            library = self.helper_slug_to_uuid(library)
        except TypeError:
            return err(BAD_LIBRARY_ID_ERROR)

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
        # TODO fix this
        permissions:  read, write,  specifies which permission to change
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
        try:
            library_uuid = self.helper_slug_to_uuid(library)
        except TypeError:
            return err(BAD_LIBRARY_ID_ERROR)

        user_editing_uid = \
            self.helper_absolute_uid_to_service_uid(absolute_uid=user_editing)

        try:
            permission_data = get_post_data(
                request,
                types=dict(
                    email=unicode,
                    permission=dict
                )
            )
        except TypeError as error:
            current_app.logger.error('Wrong type passed for POST: {0} [{1}]'
                                     .format(request.data, error))
            return err(WRONG_TYPE_ERROR)

        bad_vals = [type(v) for k,v in permission_data['permission'].iteritems() if (type(v)!=bool)]
        if len(bad_vals) > 0:
            current_app.logger.error('Wrong values passed for permissions for POST: {0} [{1}]'
                                     .format(request.data, bad_vals))
            return err(WRONG_TYPE_ERROR)

        current_app.logger.info('Requested permission changes for user {0}:'
                                ' {1} for library {2}, by user: {3}'
                                .format(permission_data['email'],
                                        permission_data,
                                        library_uuid,
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
                                   library_id=library_uuid):

            current_app.logger.error(
                'User: {0} does not have permissions to edit: {1}'
                .format(user_editing_uid, library_uuid)
            )
            return err(NO_PERMISSION_ERROR)

        try:
            self.add_permission(service_uid=secondary_service_uid,
                                library_id=library_uuid,
                                permission=permission_data['permission'])
        except PermissionDeniedError:
            current_app.logger.error('User: {0} does not have permissions to '
                                     'modify the value of: {1}'
                                     .format(user_editing_uid,
                                             permission_data['permission']))
            return err(NO_PERMISSION_ERROR)

        current_app.logger.info('...SUCCESS.')

        name = self.helper_library_name(library_uuid)

        try:
            payload_plain, payload_html = self.format_permission_payload(library_name=name,
                                                                         library_id=library,
                                                                         permission_data=permission_data)

        except (RuntimeError, ValueError) as e:
            current_app.logger.warning('Error building payload for permission data {0}, library {1}. ' +
                                       'Error message: {2}. Not sending email to {3}'.
                                       format(permission_data, name, e, permission_data['email']))
            payload_plain = None

        if payload_plain:
            current_app.logger.info('Sending email to {0} with payload: {1}'.format(permission_data['email'], payload_plain))
            try:
                msg = self.send_email(email_addr=permission_data['email'],
                                      payload_plain=payload_plain,
                                      payload_html=payload_html,
                                      email_template=PermissionsChangedEmail)
            except:
                current_app.logger.warning('Sending email to {0} failed'.format(permission_data['email']))

        return {}, 200
