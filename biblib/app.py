"""
Application
"""

import logging.config
from views import UserView, LibraryView, DocumentView, PermissionView, \
    TransferView
from models import db

from flask import Flask
from flask.ext.restful import Api
from flask.ext.discoverer import Discoverer
from flask.ext.consulate import Consul, ConsulConnectionError


def create_app(config_type='STAGING'):
    """
    Create the application and return it to the user
    :param config_type: specifies which configuration file to load. Options are
    TEST, LOCAL, and PRODUCTION.

    :return: application
    """

    app = Flask(__name__, static_folder=None)
    app.url_map.strict_slashes = False

    # Load config and logging
    Consul(app)  # load_config expects consul to be registered
    load_config(app, config_type)
    logging.config.dictConfig(
        app.config['BIBLIB_LOGGING']
    )

    # Register extensions
    api = Api(app)
    Discoverer(app)
    db.init_app(app)

    # Add the end resource end points
    api.add_resource(UserView,
                     '/libraries',
                     methods=['GET', 'POST'])

    api.add_resource(LibraryView,
                     '/libraries/<string:library>',
                     methods=['GET'])

    api.add_resource(DocumentView,
                     '/documents/<string:library>',
                     methods=['POST', 'DELETE', 'PUT'])

    api.add_resource(PermissionView,
                     '/permissions/<string:library>',
                     methods=['GET', 'POST'])

    api.add_resource(TransferView,
                     '/transfer/<string:library>',
                     methods=['POST'])

    return app

def load_config(app, config_type):
    """
    Loads configuration in the following order:
        1. config.py
        2. local_config.py (ignore failures)
        3. consul (ignore failures)
    :param app: flask.Flask application instance
    :param config_type: config file to use
    :return: None
    """

    config_dictionary = dict(
        TEST='test_config.py',
        LOCAL='local_config.py',
        PRODUCTION='config.py'
    )

    app.config.from_pyfile(config_dictionary[config_type])

    if config_type in config_dictionary.keys():
        try:
            app.config.from_pyfile(config_dictionary[config_type])
        except IOError:
            app.logger.warning('Could not find specified config file: {0}'
                               .format(config_dictionary[config_type]))
            raise
    else:
        try:
            app.config.from_pyfile('local_config.py')
        except IOError:
            app.logger.warning('Could not load local_config.py')
        try:
            app.extensions['consul'].apply_remote_config()
        except ConsulConnectionError as error:
            app.logger.warning('Could not apply config from consul: {}'
                               .format(error))

if __name__ == '__main__':
    app_ = create_app()
    app_.run(debug=True, use_reloader=False)
