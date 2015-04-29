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
from flask.ext.testing import TestCase
from flask import url_for


class TestJobEpic(TestCase):
    """
    Base class used to test the Job Epic
    """
    def create_app(self):
        """
        Create the wsgi application for flask

        :return: application instance
        """
        app_ = app.create_app()
        self.app_ = app_
        return app_

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

        url = url_for('gut.createlibrary', user=1234)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue('user' in response.json)
        self.assertTrue(response.json['user'] == 1234)

        # Mary searches for an article and then adds it to her private library.

        # Mary realises she added one that is not hers and goes back to her list
        # and deletes it from her library.

        # Happy with her library, she copies the link to the library and e-mails
        # it to the prospective employer.

        # She then checks the link herself as she is paranoid it may not work,
        # but it works fine.