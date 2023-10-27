"""
User view
"""

from biblib.utils import err, get_post_data, check_boolean
from biblib.models import User, Library, Permissions
from biblib.client import client
from biblib.views.base_view import BaseView
from flask import request, current_app
from flask_discoverer import advertise
from sqlalchemy import Boolean
from sqlalchemy.exc import IntegrityError
from biblib.views.http_errors import MISSING_USERNAME_ERROR, DUPLICATE_LIBRARY_NAME_ERROR, \
    WRONG_TYPE_ERROR, BAD_PARAMS_ERROR
from biblib.biblib_exceptions import BackendIntegrityError
import functools

class UserView(BaseView):
    """
    End point to create a library for a given user
    """

    decorators = [advertise('scopes', 'rate_limit')]
    scopes = ['user']
    rate_limit = [1000, 60*60*24]

    @staticmethod
    def create_user(absolute_uid):
        """
        Creates a user in the database with a UID from the API
        :param absolute_uid: UID from the API

        :return: no return
        """

        try:
            user = User(absolute_uid=absolute_uid)
            with current_app.session_scope() as session:
                session.add(user)
                session.commit()

        except IntegrityError as error:
            current_app.logger.error('IntegrityError. User: {0:d} was not'
                                     'added. Full traceback: {1}'
                                     .format(absolute_uid, error))
            raise

    @staticmethod
    @functools.lru_cache(maxsize=32)
    def retrieve_user_email(owner_absolute_uid):
        service = '{api}/{uid}'.format(
                    api=current_app.config['BIBLIB_USER_EMAIL_ADSWS_API_URL'],
                    uid=owner_absolute_uid
                )
        current_app.logger.info('Obtaining email of user: {0} [API UID]'
                                        .format(owner_absolute_uid))
        response = client().get(
                    service
                )
        return response

    @classmethod
    def get_libraries(cls, service_uid, absolute_uid, start=0, rows=None, sort_col="date_created", sort_order="desc", permissions=False):
        """
        Get all the libraries a user has
        :param service_uid: microservice UID of the user
        :param absolute_uid: unique UID of the user in the API
        :param start: Index of the first library to return
        :param rows: Number of libraries to return (default all)
        :param sort_col: Library column to sort on (date_created, date_last_modified, name)
        :param sort_dir: Direction sort libraries (asc, desc)

        :return: list of libraries in json format
        """

        # Get all the permissions for a user
        # This can be improved into one database call rather than having
        # one per each permission, but needs some checks in place.
        # The nested getattr calls allow us to request a column from the library model,
        # and then request the proper sort order from that column.
        with current_app.session_scope() as session:
            result = session.query(Permissions, Library)\
                .join(Permissions.library)\
                .filter(Permissions.user_id == service_uid)\
                .order_by(getattr(getattr(Library, sort_col), sort_order)())\
                .all()
            
            if rows: rows=start+rows
            
            my_libraries = []
            shared_with_me = []
            for permission, library in result[start:rows]:

                # For this library get all the people who have permissions
                users = session.query(Permissions).filter_by(
                    library_id = library.id
                ).all()

                num_documents = 0
                if library.bibcode:
                    num_documents = len(library.bibcode)

                if permission.permissions['owner']:
                    main_permission = 'owner'
                elif permission.permissions['admin']:
                    main_permission = 'admin'
                elif permission.permissions['write']:
                    main_permission = 'write'
                elif permission.permissions['read']:
                    main_permission = 'read'
                else:
                    main_permission = 'none'

                if permission.permissions['owner'] or permission.permissions['admin'] and not library.public:
                    num_users = len(users)
                elif library.public:
                    num_users = len(users)
                else:
                    num_users = 0

                if main_permission != 'owner':
                    # get the owner
                    result = session.query(Permissions, User) \
                        .join(Permissions.user) \
                        .filter(Permissions.library_id == library.id) \
                        .filter(Permissions.permissions['owner'].astext.cast(Boolean).is_(True)) \
                        .one()
                    owner_permissions, owner = result
                    owner_absolute_uid = owner.absolute_uid
                else:
                    owner_absolute_uid = absolute_uid

                response = cls.retrieve_user_email(owner_absolute_uid)

                if response.status_code != 200:
                    current_app.logger.error('Could not find user in the API'
                                             'database: {0}.'.format(owner_absolute_uid))
                    owner = 'Not available'
                else:
                    owner = response.json()['email'].split('@')[0]

                payload = dict(
                    name=library.name,
                    id='{0}'.format(cls.helper_uuid_to_slug(library.id)),
                    description=library.description,
                    num_documents=num_documents,
                    date_created=library.date_created.isoformat(),
                    date_last_modified=library.date_last_modified.isoformat(),
                    permission=main_permission,
                    public=library.public,
                    num_users=num_users,
                    owner=owner
                )

                if (permissions and main_permission in ['owner']) or not permissions: 
                    my_libraries.append(payload)
                elif permissions and main_permission in ['admin', 'read', 'write']: 
                    shared_with_me.append(payload)
            
            response = {'libraries_count': len(result), 
                        'my_libraries': my_libraries}
            
            if shared_with_me: 
                response['shared_with_me'] = shared_with_me
            
        return response

    # Methods
    def get(self):
        """
        HTTP GET request that returns all the libraries that belong to a given
        user

        :param start: The index of the library list to start on (int).  default: 0
        :param rows: The number of rows to return from the start point (int).  default: None (returns all libraries)
        :param sort_col: Library column to sort on. default: date_created (date_created, date_last_modified)
        :param sort_dir: Direction sort libraries. default: desc (asc, desc)
        :return: list of the users libraries with the relevant information

        Header:
        Must contain the API forwarded user ID of the user accessing the end
        point

        Post body:
        ----------
        No post content accepted.


        Return data:
        -----------
        name:                 <string>  Name of the library
        id:                   <string>  ID of the library
        description:          <string>  Description of the library
        num_documents:        <int>     Number of documents in the library
        date_created:         <string>  ISO date library was created
        date_last_modified:   <string>  ISO date library was last modified
        permission:           <sting>   Permission type, can be: 'read',
                                        'write', 'admin', or 'owner'
        public:               <boolean> True means it is public
        num_users:            <int>     Number of users with permissions to
                                        this library
        owner:                <string>  Identifier of the user who created
                                        the library

        Permissions:
        -----------
        The following type of user can read a library:
          - user scope (authenticated via the API)
        """

        # Check that they pass a user id
        try:
            user = self.helper_get_user_id()
        except KeyError:
            return err(MISSING_USERNAME_ERROR)
        
        try:
            get_params = request.args
            start = get_params.get('start', default=0, type=int)
            rows = get_params.get('rows', type=int)
            
            sort_col = get_params.get('sort', default='date_created', type=str)
            if sort_col not in ['date_created', 'date_last_modified', 'name']: 
                raise ValueError
            
            sort_order = get_params.get('order', default='asc', type=str)
            if sort_order not in ['asc', 'desc']:
                raise ValueError

            permissions = get_params.get('permissions', default=False, type=check_boolean)
            current_app.logger.debug("GET params: {}, start: {}, end: {}".format(get_params, start, rows))

        except ValueError:
            msg = "Failed to parse input parameters: {}. Please confirm the request is properly formatted.".format(request)
            current_app.logger.exception(msg)
            return err(BAD_PARAMS_ERROR)

        service_uid = \
            self.helper_absolute_uid_to_service_uid(absolute_uid=user)

        response = self.get_libraries(service_uid=service_uid,
                                      absolute_uid=user, 
                                      start=start, 
                                      rows=rows, 
                                      sort_col=sort_col, 
                                      sort_order=sort_order, 
                                      permissions=permissions)
        return response, 200

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
        name:                   <string>    name of the library (must be unique
                                            for that user)
        description:            <string>    description of the library
        public:                 <boolean>   is the library public to view
        bibcode (OPTIONAL):     <list>      list of bibcodes to add


        Return data:
        -----------
        name:           <string>    Name of the library
        id:             <string>    ID of the library
        description:    <string>    Description of the library


        Permissions:
        -----------
        The following type of user can create a library
          - must be logged in, i.e., scope = user
        """

        # Check that they pass a user id
        try:
            user = self.helper_get_user_id()
        except KeyError:
            return err(MISSING_USERNAME_ERROR)

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
        service_uid = \
            self.helper_absolute_uid_to_service_uid(absolute_uid=user)
        current_app.logger.info('user_API: {0:d} is now user_service: {1:d}'
                                .format(user, service_uid))

        # Create the library
        try:
            data = get_post_data(
                request,
                types=dict(
                    name=str,
                    description=str,
                    public=bool,
                    bibcode=list
                )
            )
        except TypeError as error:
            current_app.logger.error('Wrong type passed for POST: {0} [{1}]'
                                     .format(request.data, error))
            return err(WRONG_TYPE_ERROR)

        with current_app.session_scope() as session:
            try:
                library_dict = \
                    self.create_library(service_uid=service_uid, library_data=data)
            except BackendIntegrityError as error:
                current_app.logger.error(error)
                return err(DUPLICATE_LIBRARY_NAME_ERROR)
            except TypeError as error:
                current_app.logger.error(error)
                return err(WRONG_TYPE_ERROR)

            return library_dict, 200
