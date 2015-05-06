"""
Functional test

Job Epic

Storyboard is defined within the comments of the program itself
"""

__author__ = 'J. Elliott'
__maintainer__ = 'J. Elliott'
__copyright__ = 'ADS Copyright 2014, 2015'
__version__ = '1.0'
__email__ = 'ads@cfa.harvard.edu'
__status__ = 'Production'
__license__ = 'MIT'

import sys
import os

PROJECT_HOME = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(PROJECT_HOME)

import app
import json
from models import db
from flask.ext.testing import TestCase
from flask import url_for
from tests.stubdata.stub_data import StubDataLibrary


class TestJobEpic(TestCase):
    """
    Base class used to test the Job Epic
    """
    def create_app(self):
        """
        Create the wsgi application for flask

        :return: application instance
        """
        return app.create_app()

    def setUp(self):
        """
        Set up the database for use

        :return: no return
        """
        db.create_all()
        self.stub_library, self.stub_uid = StubDataLibrary().make_stub()

    def tearDown(self):
        """
        Remove/delete the database and the relevant connections

        :return: no return
        """
        db.session.remove()
        db.drop_all()

    def test_job_epic(self):
        """
        Carries out the epic 'Job', where a user wants to add their articles to
        their private libraries so that they can send it on to a prospective
        employer

        :return: no return
        """

        # Mary creates a private library and
        #   1. Gives it a name.
        #   2. Gives it a description.
        #   3. Makes it public to view.

        # Make the library
        url = url_for('createlibraryview', user=self.stub_uid)
        response = self.client.post(url, data=json.dumps(self.stub_library))

        self.assertEqual(response.status_code, 200)
        self.assertTrue('user' in response.json)
        self.assertTrue(response.json['user'] == self.stub_uid)

        # Mary searches for an article and then adds it to her private library.

        # Mary realises she added one that is not hers and goes back to her list
        # and deletes it from her library.

        # Happy with her library, she copies the link to the library and e-mails
        # it to the prospective employer.

        # She then checks the link herself as she is paranoid it may not work,
        # but it works fine.