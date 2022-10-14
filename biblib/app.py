# encoding: utf-8
"""
Application
"""

import logging.config

from werkzeug.serving import run_simple
from .views import UserView, LibraryView, DocumentView, QueryView, PermissionView, \
    TransferView, ClassicView, TwoPointOhView, OperationsView
from flask_restful import Api
from flask_discoverer import Discoverer
from flask_mail import Mail
from adsmutils import ADSFlask

def create_app(**config):
    """
    Create the application and return it to the user
    :return: application
    """

    app = ADSFlask(__name__, static_folder=None, local_config=config or {})
    app.url_map.strict_slashes = False

    # Register extensions
    api = Api(app)
    Discoverer(app)
    mail = Mail(app)

    # Add the end resource end points
    api.add_resource(UserView,
                     '/libraries',
                     methods=['GET', 'POST'])

    api.add_resource(LibraryView,
                     '/libraries/<string:library>',
                     methods=['GET'])

    api.add_resource(OperationsView,
                     '/libraries/operations/<string:library>',
                     methods=['POST'])

    api.add_resource(DocumentView,
                     '/documents/<string:library>',
                     methods=['POST', 'DELETE', 'PUT'])
    
    api.add_resource(QueryView,
                     '/query/<string:library>',
                     methods=['POST', 'GET'])

    api.add_resource(PermissionView,
                     '/permissions/<string:library>',
                     methods=['GET', 'POST'])

    api.add_resource(TransferView,
                     '/transfer/<string:library>',
                     methods=['POST'])

    api.add_resource(ClassicView,
                     '/classic',
                     methods=['GET']
                     )

    api.add_resource(TwoPointOhView,
                     '/twopointoh',
                     methods=['GET']
                     )

    return app


if __name__ == '__main__':
    run_simple('0.0.0.0', 5000, create_app(), use_reloader=False, use_debugger=False)
