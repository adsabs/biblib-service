"""
Application
"""

from flask import Flask
from views import UserView, LibraryView
from flask.ext.restful import Api
from flask.ext.discoverer import Discoverer
from models import db
from utils import setup_logging_handler

__author__ = 'J. Elliott'
__maintainer__ = 'J. Elliott'
__copyright__ = 'ADS Copyright 2015'
__version__ = '1.0'
__email__ = 'ads@cfa.harvard.edu'
__status__ = 'Production'
__credit__ = ['V. Sudilovsky']
__license__ = 'MIT'


def create_app(config_type='PRODUCTION'):
    """
    Create the application and return it to the user
    :param config_type: specifies which configuration file to load. Options are
    TEST, LOCAL, and PRODUCTION.

    :return: application
    """

    app = Flask(__name__, static_folder=None)

    app.url_map.strict_slashes = False

    config_dictionary = dict(
        TEST='test_config.py',
        LOCAL='local_config.py',
        PRODUCTION='config.py'
    )

    app.config.from_pyfile(config_dictionary['PRODUCTION'])

    if config_type in config_dictionary.keys():
        try:
            app.config.from_pyfile(config_dictionary[config_type])
        except IOError:
            app.logger.warning('Could not find specified config file: {0}'
                               .format(config_dictionary[config_type]))
            raise

    # Initiate the blueprint
    api = Api(app)

    # Add the end resource end points
    api.add_resource(UserView,
                     '/users/<int:user>/libraries/',
                     methods=['GET', 'POST'])

    api.add_resource(LibraryView,
                     '/users/<int:user>/libraries/<string:library>',
                     methods=['GET', 'POST', 'DELETE'])

    # Initiate the database from the SQL Alchemy model
    db.init_app(app)

    # Add logging
    handler = setup_logging_handler(level='DEBUG')
    app.logger.addHandler(handler)

    discoverer = Discoverer(app)
    return app

if __name__ == '__main__':
    app_ = create_app()
    app_.run(debug=True, use_reloader=False)
