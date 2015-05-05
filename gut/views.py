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

from flask.ext.restful import Resource
from flask.ext.discoverer import advertise
from models import db, User, Library, Permissions
from sqlalchemy.exc import IntegrityError


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
            # Log here
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
        _read = library_data['read']
        _write = library_data['write']
        _public = library_data['public']
        try:

            # Make the library in the library table
            library = Library(name=_name, public=_public)
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

        except IntegrityError as error:

            # Roll back the changes
            db.session.rollback()
            # Log here
            raise
        except Exception:
            db.session.rollback()

    # Methods
    def post(self, user):
        """
        HTTP POST request that creates a library for a given user
        :param user: user ID as given from the API

        :return: the response for if the library was successfully created
        """

        if not self.user_exists(absolute_uid=user):
            self.create_user(absolute_uid=user)

        return {'user': user}, 200


class GetLibraryView(Resource):
    """
    Returns the library requested for a given user.

    XXX: Check that user is not anon
    """

    def get_libraries(self, absolute_uid):

        user_libraries = \
            Library.query.filter(User.absolute_uid == absolute_uid).all()

        return user_libraries

    def get(self, user):

        user_libraries = self.get_libraries(absolute_uid=user)
        return {'libraries': user_libraries}, 200