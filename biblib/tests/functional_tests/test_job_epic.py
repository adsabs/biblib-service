"""
Functional test

Job Epic

Storyboard is defined within the comments of the program itself
"""

__author__ = 'J. Elliott'
__maintainer__ = 'J. Elliott'
__copyright__ = 'ADS Copyright 2015'
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
from tests.stubdata.stub_data import StubDataLibrary, StubDataDocument


class TestJobEpic(TestCase):
    """
    Base class used to test the Job Epic
    """
    def create_app(self):
        """
        Create the wsgi application for flask

        :return: application instance
        """
        return app.create_app(config_type='TEST')

    def setUp(self):
        """
        Set up the database for use

        :return: no return
        """
        db.create_all()
        self.stub_library, self.stub_uid = StubDataLibrary().make_stub()
        self.stub_document = StubDataDocument().make_stub()

    def tearDown(self):
        """
        Remove/delete the database and the relevant connections
!
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
        url = url_for('userview', user=self.stub_uid)
        response = self.client.post(url, data=json.dumps(self.stub_library))

        self.assertEqual(response.status_code, 200, response)
        self.assertTrue('name' in response.json)
        self.assertTrue(response.json['name'] == self.stub_library['name'])

        # Mary searches for an article and then adds it to her private library.

        # First she picks which library to add it to.
        url = url_for('userview', user=self.stub_uid)
        response = self.client.get(url)
        library_id = response.json['libraries'][0]['id']

        # Then she submits the document (in this case a bibcode) to add to the
        # library
        url = url_for('libraryview', user=self.stub_uid, library=library_id)
        self.stub_document['action'] = 'add'
        response = self.client.post(url, data=json.dumps(self.stub_document))
        self.assertEqual(response.status_code, 200, response)

        # Mary realises she added one that is not hers and goes back to her list
        # and deletes it from her library.
        url = url_for('libraryview', user=self.stub_uid, library=library_id)
        self.stub_document['action'] = 'remove'
        response = self.client.post(url, data=json.dumps(self.stub_document))
        self.assertEqual(response.status_code, 200, response)

        response = response = self.client.get(url)
        self.assertTrue(len(response.json['documents']) == 0, response.json)

        # Happy with her library, she copies the link to the library and e-mails
        # it to the prospective employer.

        # She then checks the link herself as she is paranoid it may not work,
        # but it works fine.