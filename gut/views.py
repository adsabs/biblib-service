"""
Views
"""

__author__ = 'V. Sudilovsky'
__maintainer__ = 'V. Sudilovsky'
__copyright__ = 'ADS Copyright 2014, 2015'
__version__ = '1.0'
__email__ = 'ads@cfa.harvard.edu'
__status__ = 'Production'
__license__ = 'MIT'

from flask.ext.restful import Resource
from flask.ext.discoverer import advertise
from models import db, User
from sqlalchemy.exc import IntegrityError


class CreateLibrary(Resource):
    """
    Returns the unix timestamp of the server
    """
    decorators = [advertise('scopes', 'rate_limit')]
    scopes = ['scope1', 'scope2']
    rate_limit = [1000, 60*60*24]

    def create_user(self, absolute_uid):
        """
        Creates a user in the database with a UID from the API
        :param absolute_uid: UID from API

        :return: no return
        """

        # try:
        user = User(absolute_uid=absolute_uid)
        db.session.add(user)
        db.session.commit()

        # except IntegrityError:

    def post(self, user):
        """
        HTTP POST request that creates a library for a given user
        :param user: user ID as given from the API

        :return: the response for if the library was successfully created
        """

        self.create_user(absolute_uid=user)

        return {'user': user}, 200