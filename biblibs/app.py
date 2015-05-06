"""
Application
"""

from flask import Flask
from views import CreateLibraryView, GetLibraryView
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


def create_app():
    """
    Create the application and return it to the user

    :return: application
    """

    app = Flask(__name__, static_folder=None)

    app.url_map.strict_slashes = False
    app.config.from_pyfile('config.py')
    try:
        app.config.from_pyfile('local_config.py')
    except IOError:
        pass

    # Initiate the blueprint
    api = Api(app)

    # Add the end resource end points
    api.add_resource(CreateLibraryView, '/create/<int:user>')
    api.add_resource(GetLibraryView, '/retrieve/<int:user>')

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
