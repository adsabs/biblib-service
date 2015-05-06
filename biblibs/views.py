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
from utils import get_post_data


class CreateLibraryView(Resource):
    """
    End point to create a library for a given user

    XXX: need to ignore the anon user, they should not be able to create libs
    XXX: public/private
    XXX: name of the library already exists
    XXX: must give the library name/missing input function saves time
    XXX: should implement correct rollbacks - can this be tested?
    XXX: have a helper function for absolute_uid_2_local_uid
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
            current_app.logger.error('IntegritError. User: {0:d} was not added.'
                                     ' Full traceback: {1}'
                                     .format(absolute_uid, error))
            raise

    def user_exists(self, absolute_uid):
        """
        Checks if a use exists before it would attempt to create one

        :param absolute_uid: UID from the API
        :return: boolean for if the user exists
        """

        user_count = User.query.filter(User.absolute_uid == absolute_uid).all()
        user_count = len(user_count)
        if user_count == 1:
            return True
        elif user_count == 0:
            return False

    def create_library(self, service_uid, library_data):

        _name = library_data['name']
        _description = library_data['description']
        _read = library_data['read']
        _write = library_data['write']
        _public = library_data['public']

        current_app.logger.info('Creating library for user_service: {0:d}'
                                .format(service_uid))
        try:

            # Make the library in the library table
            library = Library(name=_name,
                              description=_description,
                              public=_public)
            user = User.query.filter(User.id == service_uid).one()

            # Make the permissions
            permission = Permissions(
                read=_read,
                write=_write
            )

            # Use the ORM to link the permissions to the library and user,
            # so that no commit is required until the complete action is
            # finished. This means any rollback will not leave a single
            # library without permissions
            library.permissions.append(permission)
            user.permissions.append(permission)

            db.session.add_all([library, permission, user])
            db.session.commit()

            current_app.logger.info('Library: "{0}" created, user_service: {1:d}'
                                    .format(library.name, user.id))

        except IntegrityError as error:
            # Roll back the changes
            db.session.rollback()
            current_app.logger.error('IntegitryError, database has been rolled'
                                     'back. Caused by user_service: {0:d}. Full'
                                     'error: {1}'
                                     .format(user.id, error))
            # Log here
            raise
        except Exception:
            db.session.rollback()
            raise

    def absolute_uid_to_service_uid(self, absolute_uid):
        """
        Convert the API UID to the BibLib service ID

        :param absolute_uid: API UID
        :return: BibLib service ID
        """
        user = User.query.filter(User.absolute_uid == absolute_uid).one()
        return user.id

    # Methods
    def post(self, user):
        """
        HTTP POST request that creates a library for a given user
        :param user: user ID as given from the API

        :return: the response for if the library was successfully created
        """

        # Check if the user exists, if not, generate a user in the database
        current_app.logger.info('Checking if the user exists')
        if not self.user_exists(absolute_uid=user):
            current_app.logger.info('User: {0:d}, does not exist.'.format(user))

            self.create_user(absolute_uid=user)
            current_app.logger.info('User: {0:d}, created.'.format(user))

        # Switch to the service UID and not the API UID
        service_uid = self.absolute_uid_to_service_uid(absolute_uid=user)
        current_app.logger.info('user_API: {0:d} is now user_service: {1:d}'
                                .format(user, service_uid))

        # Create the library
        data = get_post_data(request)
        self.create_library(service_uid=service_uid, library_data=data)

        return {'user': user}, 200


class GetLibraryView(Resource):
    """
    Returns the library requested for a given user.

    XXX: Check that user is not anon
    """

    def get_libraries(self, absolute_uid):

        user_libraries = \
            Library.query.filter(User.absolute_uid == absolute_uid).all()

        output_libraries = []
        for library in user_libraries:
            payload = dict(
                name=library.name,
                description=library.description,
            )
            output_libraries.append(payload)

        return output_libraries

    def get(self, user):

        user_libraries = self.get_libraries(absolute_uid=user)
        return {'libraries': user_libraries}, 200