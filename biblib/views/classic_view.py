"""
User view
"""

from ..utils import err
from ..models import User, Library, Permissions
from ..client import client
from base_view import BaseView
from flask import current_app
from flask_discoverer import advertise
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from http_errors import MISSING_USERNAME_ERROR


class HarbourView(BaseView):
    """
    End point to import libraries from external systems
    """

    decorators = [advertise('scopes', 'rate_limit')]
    scopes = ['user']
    rate_limit = [1000, 60*60*24]
    service_url = 'default'

    @staticmethod
    def upsert_library(service_uid, library):
        """
        Upsert a library into the database. This entails:
          - Adding a library and bibcodes if there is no name conflict
          - Not adding a library if name matches, but compare bibcodes

        :param service_uid: microservice UID of the user
        :param library: dictionary of the form:
            {'name': str, 'description': str, 'documents': [str, ...., str]}

        :return: boolean for success
        """

        with current_app.session_scope() as session:
            # Make the permissions
            user = session.query(User).filter_by(id = service_uid).one()
            try:
                # we are passed the library from classic
                #   and need to find the corresponding library in bumblebee
                # the corresponding library is the one with
                #   the same name and the same owner

                # in raw sql, this is essentially
                # q = "select library.id from library,permissions where library.name='{}' and permissions.library_id=library.id and permissions.user_id={} and permissions.owner=True"
                # q = q.format(library['name'], user.id)

                # but, this must be done via the orm api
                q = session.query(Library).join(Permissions).filter(Library.id == Permissions.library_id)\
                    .filter(Permissions.user_id == user.id).filter(Permissions.owner == True).filter(Library.name == library['name'])
                lib = q.all()


                # Raise if there is not exactly one, it should be 1 or 0, but if
                # multiple are returned, there is some problem
                if len(lib) == 0:
                    raise NoResultFound
                    current_app.logger.info(
                        'User does not have a library with this name'
                    )
                elif len(lib) > 1:
                    current_app.logger.warning(
                        'More than 1 library has the same name,'
                        ' this should not happen: {}'.format(lib)
                    )
                    raise IntegrityError

                # Get the single record returned, as names are considered unique in
                # the workflow of creating libraries
                lib = lib[0]

                bibcode_before = len(lib.get_bibcodes())
                lib.add_bibcodes(library['documents'])
                bibcode_added = len(lib.get_bibcodes()) - bibcode_before
                action = 'updated'
                session.add(lib)

            except NoResultFound:
                current_app.logger.info('Creating library from scratch: {}'
                                        .format(library))
                permission = Permissions(owner=True)
                lib = Library(
                    name=library['name'][0:50],
                    description=library['description'][0:200],
                )
                lib.add_bibcodes(library['documents'])

                lib.permissions.append(permission)
                user.permissions.append(permission)

                session.add_all([lib, permission, user])

                bibcode_added = len(lib.get_bibcodes())
                action = 'created'

            session.commit()

            return {
                'library_id': BaseView.helper_uuid_to_slug(lib.id),
                'name': lib.name,
                'description': lib.description,
                'num_added': bibcode_added,
                'action': action
            }

    # Methods
    def get(self):
        """
        HTTP GET request that

        :return:

        Header:
        Must contain the API forwarded user ID of the user accessing the end
        point

        Post body:
        ----------
        No post content accepted.


        Return data:
        -----------

        Permissions:
        -----------
        The following type of user can read a library:
          - user scope (authenticated via the API)
        """
        # Check that they pass a user id
        try:
            user = self.helper_get_user_id()
        except KeyError:
            return err(MISSING_USERNAME_ERROR)

        service_uid = self.helper_absolute_uid_to_service_uid(absolute_uid=user)

        url = '{external_service}/{user_id}'.format(
            external_service=current_app.config[self.service_url],
            user_id=user
        )
        current_app.logger.info('Collecting libraries for user {} from {}'
                                .format(user, url))
        response = client().get(url)

        if response.status_code != 200:
            return response.json(), response.status_code

        resp = []
        for library in response.json()['libraries']:
            resp.append(self.upsert_library(service_uid=service_uid, library=library))

        return resp, 200


class ClassicView(HarbourView):
    """
    Wrapper for importing libraries from ADS Classic
    """
    decorators = [advertise('scopes', 'rate_limit')]
    scopes = ['user']
    rate_limit = [1000, 60*60*24]
    service_url = 'BIBLIB_CLASSIC_SERVICE_URL'


class TwoPointOhView(HarbourView):
    """
    Wrapper for importing libraries from ADS 2.0
    """
    decorators = [advertise('scopes', 'rate_limit')]
    scopes = ['user']
    rate_limit = [1000, 60*60*24]
    service_url = 'BIBLIB_TWOPOINTOH_SERVICE_URL'
