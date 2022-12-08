"""
Transfer view
"""
from biblib.utils import err, get_post_data
from biblib.models import Permissions
from biblib.views.base_view import BaseView
from flask import request, current_app
from flask_discoverer import advertise
from biblib.views.http_errors import MISSING_USERNAME_ERROR, WRONG_TYPE_ERROR, \
    API_MISSING_USER_EMAIL, NO_PERMISSION_ERROR, BAD_LIBRARY_ID_ERROR
from sqlalchemy.orm.exc import NoResultFound
from biblib.emails import PermissionsChangedEmail
from jinja2 import Environment, PackageLoader, select_autoescape

env = Environment(
    loader=PackageLoader('biblib', 'templates'),
    autoescape=select_autoescape(enabled_extensions=('html', 'xml'),
                                 default_for_string=True)
)

class TransferView(BaseView):
    """
    End point to transfer a the ownership of a library
    """

    decorators = [advertise('scopes', 'rate_limit')]
    scopes = ['user']
    rate_limit = [1000, 60*60*24]

    # Some permissions for this View
    write_allowed = ['owner']

    @staticmethod
    def transfer_ownership(current_owner_uid, new_owner_uid, library_id):
        """
        Transfers the ownership of a library from the current owner to the
        new owner. The previous owner has all permissions for that library
        removed.

        :param current_owner_uid: the user ID within this microservice
        :param new_owner_uid: the user ID within this microservice
        :param library_id: the unique ID of the library

        :return: no return
        """

        # Find the current permissions of the user
        current_app.logger.info('User {0} has requested to transfer ownership '
                                'of library {1} to user {2}'
                                .format(current_owner_uid,
                                        library_id,
                                        new_owner_uid))

        with current_app.session_scope() as session:
            current_permission = session.query(Permissions).filter(
                Permissions.user_id == current_owner_uid
            ).filter(
                Permissions.library_id == library_id
            ).one()

            # Try to get the current user's permissions
            try:
                # User already has permissions associated with it
                new_permission = session.query(Permissions).filter(
                    Permissions.user_id == new_owner_uid
                ).filter(
                    Permissions.library_id == library_id
                ).one()

                current_app.logger.info('User: {0} already has permissions for '
                                        'library {1}: {2}'
                                        .format(current_owner_uid,
                                                library_id,
                                                new_permission))

                new_permission.permissions['owner'] = True

            except NoResultFound:
                # User does not have a permission with the library
                current_app.logger.info('User {0} does not have permissions, for '
                                        'library {1} creating fresh ones.'
                                        .format(new_owner_uid, library_id))

                new_permission = Permissions(user_id=new_owner_uid,
                                             library_id=library_id,
                                             permissions={'read': False,
                                                          'write': False,
                                                          'admin': False,
                                                          'owner': True})

            session.delete(current_permission)
            session.add(new_permission)
            session.commit()

        current_app.logger.info(
            'Library {0} had ownership transferred '
            'from user: {1} to user: {2}'
            .format(library_id,
                    current_owner_uid,
                    new_owner_uid)
        )

    def post(self, library):
        """
        HTTP POST request that transfers the ownership of a library from user
        to another
        :param library: library ID

        :return: the response for if the library was successfully transfered

        Header:
        -------
        Must contain the API forwarded user ID of the user accessing the end
        point

        Post body:
        ----------
        KEYWORD, VALUE

        transfer_user:   <e-mail>   e-mail of the user the account should be
                                    transfered to

        Return data:
        -----------
        No return data

        Permissions:
        -----------
        The following type of user can transfer libraries:
          - owner
        """
        # TODO: DRY of read_access, write_access, re-write them as classmethods

        # Get the user requesting this from the header
        try:
            current_owner_api = self.helper_get_user_id()
        except KeyError:
            return err(MISSING_USERNAME_ERROR)

        # URL safe base64 string to UUID
        try:
            library_uuid = self.helper_slug_to_uuid(library)
        except TypeError:
            return err(BAD_LIBRARY_ID_ERROR)

        # Get the internal service user UID
        current_owner_service_uid = self.helper_absolute_uid_to_service_uid(
            absolute_uid=current_owner_api
        )

        # Check the post data
        try:
            transfer_data = get_post_data(
                request,
                types=dict(
                    email=str
                )
            )
        except TypeError as error:
            current_app.logger.error('Wrong type passed for POST: {0} [{1}]'
                                     .format(request.data, error))
            return err(WRONG_TYPE_ERROR)

        # Look up the user in the API database
        try:
            new_owner_api = self.helper_email_to_api_uid(transfer_data)
            current_app.logger.info('User: {0} corresponds to: {1}'
                                    .format(transfer_data['email'],
                                            new_owner_api))
        except NoResultFound:
            current_app.logger.error('User: {0} not found in the API database'
                                     .format(transfer_data['email']))
            return err(API_MISSING_USER_EMAIL)

        # Convert api user ID to service ID
        new_owner_service_uid = self.helper_absolute_uid_to_service_uid(
            absolute_uid=new_owner_api
        )
        current_app.logger.info('User: {0} is internally: {1}'
                                .format(new_owner_api, new_owner_service_uid))
        # Check permissions
        if not self.write_access(service_uid=current_owner_service_uid,
                                 library_id=library_uuid):
            current_app.logger.error(
                'User {0} has the wrong permissions to transfer the ownership'
                ' for library {1}'
                .format(current_owner_service_uid, library_uuid)
            )
            return err(NO_PERMISSION_ERROR)

        current_app.logger.info('User: {0} has permissions to transfer '
                                'library {1} to the user {2}. Attempting '
                                'transfer...'.format(current_owner_service_uid,
                                                     library_uuid,
                                                     new_owner_service_uid))

        self.transfer_ownership(current_owner_uid=current_owner_service_uid,
                                new_owner_uid=new_owner_service_uid,
                                library_id=library_uuid)

        name = self.helper_library_name(library_uuid)

        payload_plain = u'Another user has recently transferred ownership of library {0} (ID {1}) to you. ' \
                        u'\n If this is a mistake, please contact ADS Help (adshelp@cfa.harvard.edu). ' \
                        u'\n - the ADS team'.format(name, library)

        current_app.logger.info('Sending email to {0} with payload: {1}'.format(transfer_data['email'], payload_plain))

        try:
            template = env.get_template('transfer_email.html')
            payload_html = template.render(email_address=transfer_data['email'],
                                           lib_name=name,
                                           lib_id=library)
            msg = self.send_email(email_addr=transfer_data['email'],
                                  payload_plain=payload_plain,
                                  payload_html=payload_html,
                                  email_template=PermissionsChangedEmail)
        except:
            current_app.logger.warning('Sending email to {0} failed'.format(transfer_data['email']))

        return {}, 200
