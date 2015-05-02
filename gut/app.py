"""
Application
"""

import os
from flask import Blueprint
from flask import Flask
from views import UnixTime, PrintArg, ExampleApiUsage, CreateLibrary
from flask.ext.restful import Api
from flask.ext.discoverer import Discoverer
from models import db

__author__ = 'V. Sudilovsky'
__maintainer__ = 'V. Sudilovsky'
__copyright__ = 'ADS Copyright 2014, 2015'
__version__ = '1.0'
__email__ = 'ads@cfa.harvard.edu'
__status__ = 'Production'
__license__ = 'MIT'


def _create_blueprint_():
    """
    Returns an initialized Flask.Blueprint instance; This should be in a closure
    instead of the top level of a module because a blueprint can only be
    registered once. Having it at the top level creates a problem with unittests
    in that the app is created/destroyed at every test, but its blueprint is
    still the same object which was already registered.

    :return: an instantiated object of the Blueprint class
    """

    return Blueprint(
        'gut',
        __name__,
        static_folder=None,
    )


def create_app(blueprint_only=False):
    """
    Create the application and return it to the user

    :param blueprint_only: if only the blue print is wanted
    :return: blue print or application, depending upon blueprint_only
    """

    app = Flask(__name__, static_folder=None)

    app.url_map.strict_slashes = False
    app.config.from_pyfile('config.py')
    try:
        app.config.from_pyfile('local_config.py')
    except IOError:
        pass

    blueprint = _create_blueprint_()
    api = Api(blueprint)
    api.add_resource(CreateLibrary, '/create/<int:user>')
    api.add_resource(UnixTime, '/time')
    api.add_resource(PrintArg, '/print/<string:arg>')
    api.add_resource(ExampleApiUsage, '/search')

    db.init_app(app)

    if blueprint_only:
        return blueprint
    app.register_blueprint(blueprint)

    discoverer = Discoverer(app)
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, use_reloader=False)
