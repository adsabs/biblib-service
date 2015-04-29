# -*- coding: utf-8 -*-
"""
    wsgi
    ~~~~

    entrypoint wsgi script
"""

__author__ = 'V. Sudilovsky'
__maintainer__ = 'V. Sudilovsky'
__copyright__ = 'ADS Copyright 2014, 2015'
__version__ = '1.0'
__email__ = 'ads@cfa.harvard.edu'
__status__ = 'Production'
__license__ = 'MIT'

from werkzeug.serving import run_simple
from werkzeug.wsgi import DispatcherMiddleware
from gut import app

application = app.create_app()

if __name__ == "__main__":

    run_simple(
        '0.0.0.0', 4000, application, use_reloader=False, use_debugger=True
    )
