"""
Alembic migration management file
"""
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os
import sys
PROJECT_HOME = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(PROJECT_HOME)
from flask import current_app
from flask_script import Manager, Command, Option
from flask_migrate import Migrate, MigrateCommand
from biblib.models import Base, User, Permissions, Library
from biblib.app import create_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import sqlalchemy_continuum

# Load the app with the factory
app = create_app()

class DeleteStaleUsers(Command):
    """
    Compares the users that exist within the API to those within the
    microservice and deletes any stale users that no longer exist. The logic
    also takes care of the associated permissions and libraries depending on
    the cascade that has been implemented.
    """
    @staticmethod
    def run(app=app):
        """
        Carries out the deletion of the stale content
        """
        with app.app_context():
            with current_app.session_scope() as session:
                # Obtain the list of API users
                postgres_search_text = 'SELECT id FROM users;'
                result = session.execute(postgres_search_text).fetchall()
                list_of_api_users = [int(r[0]) for r in result]

                # Loop through every use in the service database
                removal_list = []
                for service_user in session.query(User).all():
                    if service_user.absolute_uid not in list_of_api_users:
                        try:
                            # Obtain the libraries that should be deleted
                            permissions = session.query(Permissions).filter(Permissions.user_id == service_user.id).all()
                            libraries = [session.query(Library).filter(Library.id == permission.library_id).one() for permission in permissions if permission.permissions['owner']]

                            # Delete all the libraries found
                            # By cascade this should delete all the permissions
                            d = [session.delete(library) for library in libraries]
                            p = [session.delete(permission) for permission in permissions]
                            d = len(d)

                            session.delete(service_user)
                            session.commit()
                            current_app.logger.info('Removed stale user: {} and {} libraries'.format(service_user, d))
                            removal_list.append(service_user)

                        except Exception as error:
                            current_app.logger.info('Problem with database, could not remove user {}: {}'
                                                    .format(service_user, error))
                            session.rollback()
                current_app.logger.info('Deleted {} stale users: {}'.format(len(removal_list), removal_list))

class DeleteObsoleteVersionsTime(Command):
    """
    Clears obsolete library versions older than chosen time.
    """
    @staticmethod
    def run(app=app, n_years=None):
        """
        Carries out the deletion of older versions
        """
        with app.app_context():

            if not n_years: n_years = current_app.config.get('REVISION_TIME', 7)

            with current_app.session_scope() as session:
                # Obtain a list of all versions older than 1 year.
                LibraryVersion = sqlalchemy_continuum.version_class(Library)
                current_date = datetime.now()
                current_offset = current_date - relativedelta(years=n_years)
                try:
                    results = session.query(LibraryVersion).filter(LibraryVersion.date_last_modified<current_offset).all()
                    d = [session.delete(revision) for revision in results]
                    d = len(d)
                    session.commit()
                    current_app.logger.info('Removed {} obsolete revisions'.format(d))
                except Exception as error:
                        current_app.logger.info('Problem with database, could not remove revisions: {}'
                                                .format(error))
                        session.rollback()

class DeleteObsoleteVersionsNumber(Command):
    """
    Limits number of revisions saved per library to n_revisions.
    """
    @staticmethod
    def run(app=app, n_revisions=None):
        """
        Carries out the deletion of older versions
        """
        if not n_revisions: n_revisions = current_app.config.get('NUMBER_REVISIONS', 7)

        with app.app_context():
            with current_app.session_scope() as session:
                LibraryVersion = sqlalchemy_continuum.version_class(Library)
                for library in session.query(Library).all():
                    try:
                        #for library in libraries:
                        revisions = session.query(LibraryVersion).filter_by(id=library.id).all()
                        # Obtain the revisions for a given library
                        current_app.logger.debug('Found {} revisions for library: {}'.format(len(revisions), library.id))
                        d = [session.delete(revision) for revision in revisions[:-n_revisions]]
                        #deletes all but the n_revisions most recent revisions.
                        d = len(d)
                        session.commit()
                        current_app.logger.info('Removed {} obsolete revisions for library: {}'.format(d, library.id))

                    except Exception as error:
                        current_app.logger.info('Problem with database, could not remove revisions for library {}: {}'
                                                .format(library, error))
                        session.rollback()

# Setup the command line arguments using Flask-Script
manager = Manager(app)
manager.add_command('syncdb', DeleteStaleUsers())
manager.add_command('clean_versions_time', DeleteObsoleteVersionsTime())
manager.add_command('clean_versions_number', DeleteObsoleteVersionsNumber())

if __name__ == '__main__':
    manager.run()
