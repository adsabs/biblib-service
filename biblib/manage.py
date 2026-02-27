import os
import sys
import click
from biblib.app import create_app
from biblib.models import User, Permissions, Library, Notes
from flask import current_app
from datetime import datetime
from dateutil.relativedelta import relativedelta
import sqlalchemy_continuum

class DeleteStaleUsers:
    """
    Compares the users that exist within the API to those within the
    microservice and deletes any stale users that no longer exist.
    """
    def run(self, app=None):
        if app is None:
            app = create_app()
        with app.app_context():
            with current_app.session_scope() as session:
                # Obtain the list of API users
                postgres_search_text = 'SELECT id FROM users;'
                result = session.execute(postgres_search_text).fetchall()
                list_of_api_users = [int(r[0]) for r in result]

                # Loop through every user in the service database
                removal_list = []
                for service_user in session.query(User).all():
                    if service_user.absolute_uid not in list_of_api_users:
                        try:
                            # Obtain the libraries that should be deleted
                            permissions = session.query(Permissions).filter(
                                Permissions.user_id == service_user.id
                            ).all()
                            
                            libraries = [
                                session.query(Library).filter(Library.id == permission.library_id).one() 
                                for permission in permissions if permission.permissions['owner']
                            ]

                            # Delete all the libraries found
                            # By cascade this should delete all the permissions
                            for library in libraries:
                                session.delete(library)
                            for permission in permissions:
                                session.delete(permission)
                            
                            session.delete(service_user)
                            session.commit()
                            
                            d_len = len(libraries)
                            current_app.logger.info('Removed stale user: {} and {} libraries'.format(service_user, d_len))
                            
                            removal_list.append(service_user)
                            
                        except Exception as error:
                            current_app.logger.info('Problem with database, could not remove user {}: {}'
                                                    .format(service_user, error))
                            session.rollback()
                
                current_app.logger.info('Deleted {} stale users: {}'.format(len(removal_list), removal_list))

class DeleteObsoleteVersionsTime:
    """
    Clears obsolete library and notes versions older than chosen time.
    """
    def run(self, n_years=None, app=None):
        if app is None:
            app = create_app()
        with app.app_context():
            if not n_years:
                n_years = current_app.config.get('REVISION_TIME', 7)

            with current_app.session_scope() as session:
                # Obtain a list of all versions older than chosen time.
                LibraryVersion = sqlalchemy_continuum.version_class(Library)
                NotesVersion = sqlalchemy_continuum.version_class(Notes)

                current_date = datetime.now()
                current_offset = current_date - relativedelta(years=n_years)

                try:
                    library_results = session.query(LibraryVersion).filter(
                        LibraryVersion.date_last_modified < current_offset
                    ).all()
                    notes_results = session.query(NotesVersion).filter(
                        NotesVersion.date_last_modified < current_offset
                    ).all()

                    for revision in library_results:
                        session.delete(revision)
                    for revision in notes_results:
                        session.delete(revision)

                    session.commit()

                    current_app.logger.info('Removed {} obsolete library revisions'.format(len(library_results)))
                    current_app.logger.info('Removed {} obsolete notes revisions'.format(len(notes_results)))

                except Exception as error:
                    current_app.logger.info('Problem with database, could not remove revisions: {}'
                                            .format(error))
                    session.rollback()

class DeleteObsoleteVersionsNumber:
    """
    Limits number of revisions saved per entity to n_revisions.
    """
    def run(self, n_revisions=None, app=None):
        if app is None:
            app = create_app()
        with app.app_context():
            if not n_revisions:
                n_revisions = current_app.config.get('NUMBER_REVISIONS', 7)

            def limit_revisions(session, entity_class, n_revisions):
                VersionClass = sqlalchemy_continuum.version_class(entity_class)
                entities = session.query(entity_class).all()

                for entity in entities:
                    try:
                        revisions = session.query(VersionClass).filter_by(id=entity.id).order_by(
                            VersionClass.date_last_modified.asc()
                        ).all()
                        
                        current_app.logger.debug('Found {} revisions for entity: {}'.format(len(revisions), entity.id))
                        
                        if len(revisions) > n_revisions:
                            obsolete = revisions[:-n_revisions]
                            for r in obsolete:
                                session.delete(r)
                            
                            session.commit()
                            
                            current_app.logger.info('Removed {} obsolete revisions for entity: {}'.format(len(obsolete), entity.id))
                            
                    except Exception as error:
                        current_app.logger.info('Problem with the database, could not remove revisions for entity {}: {}'
                                                .format(entity, error))
                        session.rollback()

            with current_app.session_scope() as session:
                limit_revisions(session, Library, n_revisions)
                limit_revisions(session, Notes, n_revisions)

# CLI part for backward compatibility running as script
@click.group()
def manager():
    """Management script for the Biblib service."""
    pass

@manager.command()
def syncdb():
    """Compares microservice users to API users and deletes stale users."""
    DeleteStaleUsers().run()

@manager.command(name='clean_versions_time')
@click.option('--years', default=None, type=int, help='Number of years to keep')
def clean_versions_time(years):
    """Clears obsolete revisions older than chosen time."""
    DeleteObsoleteVersionsTime().run(n_years=years)

@manager.command(name='clean_versions_number')
@click.option('--revisions', default=None, type=int, help='Maximum revisions to keep')
def clean_versions_number(revisions):
    """Limits number of revisions saved per entity."""
    DeleteObsoleteVersionsNumber().run(n_revisions=revisions)

if __name__ == '__main__':
    manager()

