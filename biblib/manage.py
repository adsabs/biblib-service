"""
Alembic migration management file
"""

__author__ = 'J. Elliott'
__maintainer__ = 'J. Elliott'
__copyright__ = 'ADS Copyright 2015'
__version__ = '1.0'
__email__ = 'ads@cfa.harvard.edu'
__status__ = 'Production'
__license__ = 'MIT'

from flask.ext.script import Manager
from flask.ext.migrate import Migrate, MigrateCommand
from app import create_app
from models import db

# Load the app with the factory
app = create_app(config_type='TEST')

# Set up the alembic migration
migrate = Migrate(app, db)

# Setup the command line arguments using Flask-Script
manager = Manager(app)
manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()