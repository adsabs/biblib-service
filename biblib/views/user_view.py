"""
User view
"""

from ..utils import err, get_post_data
from ..models import User, Library, Permissions
from ..client import client
from base_view import BaseView
from flask import request, current_app
from flask_discoverer import advertise
from sqlalchemy.exc import IntegrityError
from http_errors import MISSING_USERNAME_ERROR, DUPLICATE_LIBRARY_NAME_ERROR, \
    WRONG_TYPE_ERROR
from ..biblib_exceptions import BackendIntegrityError

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

    @classmethod
    def get_libraries(cls, service_uid, absolute_uid):
        """
        Get all the libraries a user has
        :param service_uid: microservice UID of the user
        :param absolute_uid: unique UID of the user in the API

        :return: list of libraries in json format
        """

        # Get all the permissions for a user
        # This can be improved into one database call rather than having
        # one per each permission, but needs some checks in place.
        with current_app.session_scope() as session:
            result = session.query(Permissions, Library)\
                .join(Permissions.library)\
                .filter(Permissions.user_id == service_uid)\
                .all()

            output_libraries = []
            for permission, library in result:

                # For this library get all the people who have permissions
                users = session.query(Permissions).filter_by(
                    library_id = library.id
                ).all()

                num_documents = 0
                if library.bibcode:
                    num_documents = len(library.bibcode)

                if permission.owner:
                    main_permission = 'owner'
                elif permission.admin:
                    main_permission = 'admin'
                elif permission.write:
                    main_permission = 'write'
                elif permission.read:
                    main_permission = 'read'
                else:
                    main_permission = 'none'

                if permission.owner or permission.admin and not library.public:
                    num_users = len(users)
                elif library.public:
                    num_users = len(users)
                else:
                    num_users = 0

                service = '{api}/{uid}'.format(
                    api=current_app.config['BIBLIB_USER_EMAIL_ADSWS_API_URL'],
                    uid=absolute_uid
                )
                current_app.logger.info('Obtaining email of user: {0} [API UID]'
                                        .format(absolute_uid))
                response = client().get(
                    service
                )

                if response.status_code != 200:
                    current_app.logger.error('Could not find user in the API'
                                             'database: {0}.'.format(service))
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

                output_libraries.append(payload)

            return output_libraries

    # Methods
    def get(self):
        """
        HTTP GET request that returns all the libraries that belong to a given
        user

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

        service_uid = \
            self.helper_absolute_uid_to_service_uid(absolute_uid=user)

        user_libraries = self.get_libraries(service_uid=service_uid,
                                            absolute_uid=user)
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
                    name=unicode,
                    description=unicode,
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
