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
from biblib.models import Base, User, Permissions, Library, Notes
from biblib.app import create_app
from sqlalchemy import create_engine, desc
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
                            d_len = len(d)

                            session.delete(service_user)
                            session.commit()
                            current_app.logger.info('Removed stale user: {} and {} libraries'.format(service_user, d_len))
                            removal_list.append(service_user)

                        except Exception as error:
                            current_app.logger.info('Problem with database, could not remove user {}: {}'
                                                    .format(service_user, error))
                            session.rollback()
                current_app.logger.info('Deleted {} stale users: {}'.format(len(removal_list), removal_list))

class DeleteObsoleteVersionsTime(Command):
    """
    Clears obsolete library and notes versions older than chosen time.
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
                NotesVersion = sqlalchemy_continuum.version_class(Notes)
                current_date = datetime.now()
                current_offset = current_date - relativedelta(years=n_years)
                try:
                    library_results = session.query(LibraryVersion).filter(LibraryVersion.date_last_modified<current_offset).all()
                    notes_results = session.query(NotesVersion).filter(NotesVersion.date_last_modified<current_offset).all() 

                    d_library = [session.delete(revision) for revision in library_results]
                    d_notes = [session.delete(revision) for revision in notes_results] 

                    d_library_len = len(d_library)
                    d_notes_len = len(d_notes)
                    session.commit()
                    current_app.logger.info('Removed {} obsolete library revisions'.format(d_library_len))
                    current_app.logger.info('Removed {} obsolete notes revisions'.format(d_notes_len))
                except Exception as error:
                        current_app.logger.info('Problem with database, could not remove revisions: {}'
                                                .format(error))
                        session.rollback()

class DeleteObsoleteVersionsNumber(Command):
    """
    Limits number of revisions saved per entity to n_revisions.
    """
    @staticmethod
    def limit_revisions(session, entity_class, n_revisions):
        VersionClass = sqlalchemy_continuum.version_class(entity_class)
        entities = session.query(entity_class).all()

        for entity in entities:
            try:
                revisions = session.query(VersionClass).filter_by(id=entity.id).order_by(VersionClass.date_last_modified.asc()).all()
                current_app.logger.debug('Found {} revisions for entity: {}'.format(len(revisions), entity.id))
                obsolete_revisions = revisions[:-n_revisions]
                deleted_revisions = [session.delete(revision) for revision in obsolete_revisions]
                deleted_revisions_len = len(deleted_revisions)
                session.commit()
                current_app.logger.info('Removed {} obsolete revisions for entity: {}'.format(deleted_revisions_len, entity.id))

            except Exception as error:
                current_app.logger.info('Problem with the database, could not remove revisions for entity {}: {}'
                                        .format(entity, error))
                session.rollback()

    @staticmethod
    def run(app=app, n_revisions=None):
        if not n_revisions:
            n_revisions = current_app.config.get('NUMBER_REVISIONS', 7)

        with app.app_context():
            with current_app.session_scope() as session:
                DeleteObsoleteVersionsNumber.limit_revisions(session, Library, n_revisions)
                DeleteObsoleteVersionsNumber.limit_revisions(session, Notes, n_revisions)



# Setup the command line arguments using Flask-Script
manager = Manager(app)
manager.add_command('syncdb', DeleteStaleUsers())
manager.add_command('clean_versions_time', DeleteObsoleteVersionsTime())
manager.add_command('clean_versions_number', DeleteObsoleteVersionsNumber())

if __name__ == '__main__':
    manager.run()
