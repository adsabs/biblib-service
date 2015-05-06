"""
Test webservices
"""

__author__ = 'J. Elliott'
__maintainer__ = 'J. Elliott'
__copyright__ = 'ADS Copyright 2015'
__version__ = '1.0'
__email__ = 'ads@cfa.harvard.edu'
__status__ = 'Production'
__credit__ = ['V. Sudilovsky']
__license__ = 'MIT'

import sys
import os

PROJECT_HOME = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(PROJECT_HOME)

import app
import unittest
import json
from flask.ext.testing import TestCase
from flask import url_for
from models import db
from tests.stubdata.stub_data import StubDataLibrary


class TestWebservices(TestCase):
    """
    Tests that each route is an http response
    """
  
    def create_app(self):
        """
        Create the wsgi application

        :return: application instance
        """
        app_ = app.create_app(config_type='TEST')
        return app_

    def setUp(self):
        """
        Set up the database for use

        :return: no return
        """

        db.create_all()
        self.stub_library, self.stub_user_id = StubDataLibrary().make_stub()

    def tearDown(self):
        """
        Remove/delete the database and the relevant connections

        :return: no return
        """

        db.session.remove()
        db.drop_all()

    def test_create_library_resource(self):
        """
        Test the /create route

        :return: no return
        """

        # Make the library
        url = url_for('userview', user=self.stub_user_id)
        r = self.client.post(url, data=json.dumps(self.stub_library))
        self.assertEqual(r.status_code, 200)
        for key in ['name', 'id']:
            self.assertIn(key, r.json)

        # Check the library exists in the database
        url = url_for('userview', user=self.stub_user_id)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        for library in r.json['libraries']:
            self.assertIn(self.stub_library['name'], library['name'])
            self.assertIn(
                self.stub_library['description'],
                library['description']
            )

if __name__ == '__main__':
    unittest.main(verbosity=2)
