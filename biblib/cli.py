import click
from flask import current_app
from flask.cli import with_appcontext
from biblib.models import User, Permissions, Library, Notes
from datetime import datetime
from dateutil.relativedelta import relativedelta
import sqlalchemy_continuum

@click.group()
def biblib():
    """Commands for the biblib service"""
    pass

@biblib.command()
@with_appcontext
def syncdb():
    """
    Compares the users that exist within the API to those within the
    microservice and deletes any stale users that no longer exist. The logic
    also takes care of the associated permissions and libraries depending on
    the cascade that has been implemented.
    """
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
                    permissions = session.query(Permissions).filter(
                        Permissions.user_id == service_user.id
                    ).all()
                    
                    libraries = [
                        session.query(Library).filter(Library.id == p.library_id).one() 
                        for p in permissions if p.permissions['owner']
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

@biblib.command(name='clean_versions_time')
@click.option('--years', default=None, type=int, help='Number of years to keep')
@with_appcontext
def clean_versions_time(years):
    """
    Clears obsolete library and notes versions older than chosen time.
    """
    if not years:
        years = current_app.config.get('REVISION_TIME', 7)

    with current_app.session_scope() as session:
        # Obtain a list of all versions older than chosen time.
        LibraryVersion = sqlalchemy_continuum.version_class(Library)
        NotesVersion = sqlalchemy_continuum.version_class(Notes)

        current_date = datetime.now()
        current_offset = current_date - relativedelta(years=years)

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

@click.option('--revisions', default=None, type=int, help='Maximum revisions to keep')
@biblib.command(name='clean_versions_number')
@with_appcontext
def clean_versions_number(revisions):
    """
    Limits number of revisions saved per entity to n_revisions.
    """
    if not revisions:
        revisions = current_app.config.get('NUMBER_REVISIONS', 7)

    def limit_revisions(session, entity_class, n_revisions):
        VersionClass = sqlalchemy_continuum.version_class(entity_class)
        entities = session.query(entity_class).all()

        for entity in entities:
            try:
                revs = session.query(VersionClass).filter_by(id=entity.id).order_by(
                    VersionClass.date_last_modified.asc()
                ).all()
                
                current_app.logger.debug('Found {} revisions for entity: {}'.format(len(revs), entity.id))
                
                if len(revs) > n_revisions:
                    obsolete = revs[:-n_revisions]
                    for r in obsolete:
                        session.delete(r)
                    
                    session.commit()
                    
                    current_app.logger.info('Removed {} obsolete revisions for entity: {}'.format(len(obsolete), entity.id))
                    
            except Exception as error:
                current_app.logger.info('Problem with the database, could not remove revisions for entity {}: {}'
                                        .format(entity, error))
                session.rollback()

    with current_app.session_scope() as session:
        limit_revisions(session, Library, revisions)
        limit_revisions(session, Notes, revisions)
