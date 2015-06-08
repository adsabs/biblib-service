"""
Alembic migration management file
"""

from flask.ext.script import Manager, Command
from flask.ext.migrate import Migrate, MigrateCommand
from models import db
from app import create_app


class CreateDatabase(Command):
    """
    Creates the database based on models.py
    """
    @staticmethod
    def run():
        """
        Creates the database in the application context
        :return:
        """
        with create_app(config_type='TEST').app_context():
            db.create_all()
            db.session.commit()


class DestroyDatabase(Command):
    """
    Creates the database based on models.py
    """
    @staticmethod
    def run():
        """
        Creates the database in the application context
        :return:
        """
        with create_app(config_type='TEST').app_context():
            db.session.remove()
            db.drop_all()


# Load the app with the factory
app = create_app(config_type='TEST')

# Set up the alembic migration
migrate = Migrate(app, db, compare_type=True)

# Setup the command line arguments using Flask-Script
manager = Manager(app)
manager.add_command('db', MigrateCommand)
manager.add_command('createdb', CreateDatabase())
manager.add_command('destroydb', DestroyDatabase())

if __name__ == '__main__':
    manager.run()
