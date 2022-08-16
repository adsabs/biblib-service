"""
Base view
"""
from unittest.mock import NonCallableMagicMock
import uuid
import base64

from ..views import DEFAULT_LIBRARY_NAME_PREFIX, DEFAULT_LIBRARY_DESCRIPTION, \
    USER_ID_KEYWORD
from flask import request, current_app, make_response, jsonify
from flask_restful import Resource
from flask_mail import Message
from ..models import User, Library, Permissions
from ..client import client
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import Boolean
from ..biblib_exceptions import BackendIntegrityError, PermissionDeniedError
from ..utils import uniquify
from ..emails import Email

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

        :return: library_slug: base64 URL safe slug, string
        """
        library_slug = base64.urlsafe_b64encode(library_uuid.bytes)
        library_slug = library_slug.rstrip(b'=\n').replace(b'/', b'_')
        library_slug = library_slug.decode('utf-8')
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

        :return: None
        """

        with current_app.session_scope() as session:
            try:
                user = User(absolute_uid=absolute_uid)
                session.add(user)
                session.commit()

                current_app.logger.info('Successfully created user: {0} [API] as '
                                        '{1} [Microservice]'
                                        .format(absolute_uid, user.id))
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

        with current_app.session_scope() as session:
            user_count = session.query(User).filter_by(absolute_uid = absolute_uid).all()
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

        with current_app.session_scope() as session:
            user = session.query(User).filter_by(absolute_uid = absolute_uid).one()
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
        with current_app.session_scope() as session:
            try:
                permissions = session.query(Permissions).filter_by(
                    library_id = library_id,
                    user_id = service_uid
                ).one()

                return getattr(permissions, 'permissions')[access_type]

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
        with current_app.session_scope() as session:
            try:
                session.query(Library).filter_by(id = library_id).one()
                return True
            except NoResultFound:
                return False

    @staticmethod
    def helper_library_name(library_id):
        """
        Given a library ID, returns the name of the library.
        :return: library name
        """
        with current_app.session_scope() as session:
            try:
                library = session.query(Library).filter_by(id=library_id).one()
                return library.name
            except NoResultFound:
                return None

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
        with current_app.session_scope() as session:
            library_names = \
                [i.library.name for i in
                 session.query(Permissions)\
                     .filter_by(user_id = service_uid)\
                     .filter(Permissions.permissions['owner'].astext.cast(Boolean).is_(True))\
                     .all()]

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

    @classmethod
    def create_library(cls, service_uid, library_data):
        """
        Creates a library for a user

        :param service_uid: the user ID within this microservice
        :param library_data: content needed to create a library

        :return: library dict
        """

        library_data = BaseView.helper_validate_library_data(
            service_uid=service_uid,
            library_data=library_data
        )
        _name = library_data.get('name', 'Untitled Library')
        _description = library_data.get('description', 'My ADS library')
        _public = bool(library_data.get('public', False))
        _bibcode = library_data.get('bibcode', False)

        if _name and len(_name) > 50:
            _name = _name[:47] + '...'

        if _description and len(_description) > 200:
            _description = _description[:197] + '...'

        with current_app.session_scope() as session:
            try:
                # Make the library in the library table
                library = Library(name=_name,
                                  description=_description,
                                  public=_public)

                # If the user supplies bibcodes
                if _bibcode and isinstance(_bibcode, list):

                    # Ensure unique content
                    _bibcode = uniquify(_bibcode)
                    current_app.logger.info('User supplied bibcodes: {0}'
                                            .format(_bibcode))
                    library.add_bibcodes(_bibcode)
                elif _bibcode:
                    current_app.logger.error('Bibcode supplied not a list: {0}'
                                             .format(_bibcode))
                    raise TypeError('Bibcode should be a list.')

                user = session.query(User).filter_by(id=service_uid).one()

                # Make the permissions
                permission = Permissions(
                    permissions={'read': False, 'write': False, 'admin': False, 'owner': True},
                )

                # Use the ORM to link the permissions to the library and user,
                # so that no commit is required until the complete action is
                # finished. This means any rollback will not leave a single
                # library without permissions
                library.permissions.append(permission)
                user.permissions.append(permission)

                session.add_all([library, permission, user])
                session.commit()

                current_app.logger.info(u'Library: "{0}" made, user_service: {1:d}'
                                        .format(library.name, user.id))

                library_dict = dict(
                    name=library.name,
                    id='{0}'.format(cls.helper_uuid_to_slug(library.id)),
                    description=library.description,
                )
                # If they added bibcodes include in the response
                if hasattr(library, 'bibcode') and library.bibcode:
                    library_dict['bibcode'] = library.get_bibcodes()
                return library_dict

            except IntegrityError as error:
                # Roll back the changes
                session.rollback()
                current_app.logger.error('IntegitryError, database has been rolled'
                                         'back. Caused by user_service: {0:d}.'
                                         'Full error: {1}'
                                         .format(user.id, error))
                # Log here
                raise
            except Exception:
                session.rollback()
                raise

    @staticmethod
    def send_email(email_addr, payload_plain, payload_html, email_template=Email):
        """
        Encrypts a payload using itsDangerous.TimeSerializer, adding it along with a base
        URL to an email template. Sends an email with this data using the current app's
        'mail' extension.

        :param email_addr:
        :type email_addr: basestring
        :param payload_plain: plain text version of message body
        :param payload_html: HTML-formatted version of message body
        :param email_template: emails.Email

        :return: msg,token
        :rtype flask.ext.mail.Message, basestring
        """

        msg = Message(subject=email_template.subject,
                      recipients=[email_addr],
                      body=email_template.msg_plain.format(payload=payload_plain),
                      html=email_template.msg_html.format(payload=payload_html))
        # TODO make this async?
        current_app.extensions['mail'].send(msg)

        current_app.logger.info('Email sent to {0} with payload: {1}'.format(msg.recipients, msg.body))
        return msg

    @staticmethod
    def solr_big_query(
            bibcodes,
            start=0,
            rows=20,
            sort='date desc',
            fl='bibcode'
    ):
        """
        A thin wrapper for the solr bigquery service.

        :param bibcodes: bibcodes
        :type bibcodes: list

        :param start: start index
        :type start: int

        :param rows: number of rows
        :type rows: int

        :param sort: how the response should be sorted
        :type sort: str

        :param fl: Solr fields to be returned
        :type fl: str

        :return: bibcodes from solr bigquery endpoint response
        """

        bibcodes_string = 'bibcode\n' + '\n'.join(bibcodes)

        # We need at least bibcode and alternate bibcode for other methods
        # to work properly
        if fl == '':
            fl = 'bibcode,alternate_bibcode'
        else:
            fl_split = fl.split(',')
            for required_fl in ['bibcode', 'alternate_bibcode']:
                if required_fl not in fl_split:
                    fl = '{},{}'.format(fl, required_fl)

        params = {
            'q': '*:*',
            'wt': 'json',
            'fl': fl,
            'rows': rows,
            'start': start,
            'fq': '{!bitset}',
            'sort': sort
        }

        headers = {
            'Content-Type': 'big-query/csv',
            'Authorization': current_app.config.get('SERVICE_TOKEN', request.headers.get('X-Forwarded-Authorization', request.headers.get('Authorization', '')))
        }
        current_app.logger.info('Querying Solr bigquery microservice: {0}, {1}'
                                .format(params,
                                        bibcodes_string.replace('\n', ',')))
        solr_resp = client().post(
            url=current_app.config['BIBLIB_SOLR_BIG_QUERY_URL'],
            params=params,
            data=bibcodes_string,
            headers=headers
        )
        return solr_resp

    @staticmethod
    def standard_ADS_bibcode_query(input_bibcodes=[],
            start=0,
            rows=20,
            sort='date desc',
            fl='bibcode', 
            **kwargs):
        """
        Validates identifiers by collecting all bibcodes returned from a standard query.
        """
        headers = {
            'Content-Type': 'application/json',
            'Authorization': current_app.config.get('SERVICE_TOKEN', request.headers.get('X-Forwarded-Authorization', request.headers.get('Authorization', '')))
        }
        if kwargs.get('params'):
            params = kwargs.get('params')
            solr_query_fields=["q", "rows", "start", "fl", "fq", "sort"]
            valid_params = {}
            
            for key in params.keys():
                if key in solr_query_fields:
                    valid_params[key] = params.get(key)
                else:
                    error_resp = make_response(jsonify({"error":"Invalid /search parameters specified."}),400)
                    for key in headers.keys():
                        error_resp.headers[key] = headers[key]
                    return error_resp

            if params.get('fl', '') == '':
                params['fl'] = 'bibcode'
            
            else:
                fl_split = valid_params.get('fl').split(',')
                for required_fl in ['bibcode']:
                    if required_fl not in fl_split:
                        valid_params['fl'] = '{},{}'.format(valid_params.get('fl'), required_fl)

            valid_params['wt'] = 'json'
            valid_params['rows'] = min(params.get('rows', current_app.config.get('BIBLIB_MAX_ROWS')), current_app.config.get('BIBLIB_MAX_ROWS'))

        else:
            bibcode_query ="identifier:("+" OR ".join(input_bibcodes)+")"
            if fl == '':
                fl = 'bibcode'
            else:
                fl_split = fl.split(',')
                for required_fl in ['bibcode']:
                    if required_fl not in fl_split:
                        fl = '{},{}'.format(fl, required_fl)

            params = {
                'q': bibcode_query,
                'wt': 'json',
                'fl': fl,
                'rows': rows,
                'start': start,
                'sort': sort
            }

        
        current_app.logger.info('Querying Search microservice: {0}'
                                .format(params))
        solr_resp = client().get(
            url=current_app.config['BIBLIB_SOLR_SEARCH_URL'],
            params=params,
            headers=headers
        )
        return solr_resp