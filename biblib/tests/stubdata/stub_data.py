"""
Contains stub data that is to be used within the tests to avoid DRY
"""

import json
import factory
from faker import Faker
from models import User, Library
from views import USER_ID_KEYWORD

faker = Faker()

def fake_bibcode():
    """
    Generate a fake bibliographic code used by the ADS. This should be 19
    digits maximum. Starts with the year, includes the providers abbreviated
    name. The last letter is the authors first letter of the second name. This
    is sufficient for the purposes of the tests.

    :return: bibcode
    """
    year = faker.year()
    author = faker.random_letter().upper()
    provider = author
    for i in range(2):
        provider += faker.random_letter().upper()

    bibcode = '{year}.....{provider}......{author}'\
        .format(year=year,
                provider=provider,
                author=author)
    
    return bibcode


def fake_biblist(nb_codes):
    """
    Generate a list of fake bibcodes
    :param nb_codes: number of bibcodes to generate

    :return: list of bibcodes
    """

    bibcodes = []
    for i in range(nb_codes):
        bibcodes.append(fake_bibcode())
    return bibcodes


class UserFactory(factory.Factory):
    """
    Factory for creating fake User models
    """
    class Meta:
        """
        Defines the model that describes this factory
        """
        model = User

    id = factory.Sequence(lambda n: n)
    absolute_uid = factory.LazyAttribute(lambda x: faker.random_int())
    email = factory.LazyAttribute(lambda x: faker.email())


class LibraryFactory(factory.Factory):
    """
    Factory for creating fake Library models
    """

    class Meta:
        """
        Defines the model that describes this factory
        """
        model = Library

    name = factory.LazyAttribute(lambda x: faker.sentence(nb_words=3)[:49])
    description = \
        factory.LazyAttribute(lambda x: faker.sentence(nb_words=5)[:49])
    public = False
    read = False
    write = False
    bibcode = factory.LazyAttribute(lambda x: fake_biblist(nb_codes=1))


class UserShop(object):
    """
    A thin wrapper class that utilises the UserFactory to create extra stub
    data that is expected to be used within the webservices.

    PermissionView
    ==============

    POST
    ----
    email: email of the user to apply the permission
    permission: permission to change
    value: boolean for the permission
    """
    def __init__(self, name=None):
        """
        Constructor of the class

        :return: no return
        """
        if name:
            self.name = name
        else:
            self.name = 'Noname'

        self.stub = UserFactory.stub()
        self.headers = {}

        for key in self.stub.__dict__.keys():
            setattr(self, key, self.stub.__dict__[key])

        self.create_header()

    def create_header(self):
        """
        Create the header expected to come from the API

        :return: no return
        """
        self.headers = {USER_ID_KEYWORD: self.absolute_uid}

    def permission_view_post_data(self, permission, value):
        """
        Expected data to be sent in a POST request to the PermissionView
        end point, /permissions/<>
        :param permission: permission to change
        :param value: value of the permission (boolean)

        :return: POST data in dictionary format
        """
        post_data = dict(
            email=self.email,
            permission=permission,
            value=value
        )

        return post_data

    def permission_view_post_data_json(self, permission, value):
        """
        Expected data to be sent in a POST request to the PermissionView.
        This has been turned into json format.

        :param permission: permission to change
        :param value: value of the permission (boolean)

        :return: POST data in JSON format
        """
        post_data = self.permission_view_post_data(permission, value)
        return json.dumps(post_data)

class LibraryShop(object):
    """
    A thin wrapper class that utilises the UserFactory to create extra stub
    data that is expected to be used within the webservices.

    UserView
    ========

    POST
    ----
    name: Name of the library
    description: Description of the library
    public: Boolean (defaults to False)


    LibraryView
    ============
    GET
    ---


    DocumentView
    ============
    POST
    ----
    bibcode: bibcode
    action: add/remove

    PUT
    ----
    name: name
    description: description
    """

    def __init__(self, **kwargs):
        """
        Constructor of the class
        :param **kwargs: keyword arguments to pass on

        :return: no return
        """
        self.stub = LibraryFactory.stub()

        self.user_view_post_data = None
        self.user_view_post_data_json = None

        self.kwargs = kwargs

        self.want_bibcode = False

        self.init_values()

    def init_values(self):
        """
        Initialise all the values

        :return:
        """
        for key in self.stub.__dict__.keys():
            setattr(self, key, self.stub.__dict__[key])

        if self.kwargs:
            for key in self.kwargs:
                if key in self.__dict__.keys():
                    setattr(self, key, self.kwargs[key])

        self.create_user_view_post_data()

    def create_user_view_post_data(self):
        """
        Expected data to be sent in a POST request to the UserView,
        end point, /libraries

        :return: no return
        """
        post_data = dict(
            name=self.name,
            description=self.description,
            public=self.public
        )

        if self.want_bibcode:
            post_data['bibcode'] = self.bibcode

        json_data = json.dumps(post_data)

        self.user_view_post_data = post_data
        self.user_view_post_data_json = json_data

    def document_view_post_data(self, action='add'):
        """
        Expected data to be sent in a POST request to the DocumentView
        end point, /documents/<>
        :param action: action to perform with the bibcode (add, remove)

        :return: POST data in dictionary format
        """
        post_data = dict(
            bibcode=self.bibcode,
            action=action
        )
        return post_data

    def document_view_post_data_json(self, action='add'):
        """
        Expected data to be sent in a POST request to the DocumentView
        Converted into JSON.
        :param action: action to perform with the bibcode (add, remove)

        :return: POST data in JSON format
        """
        post_data = self.document_view_post_data(action)
        return json.dumps(post_data)

    def document_view_put_data(self, name='', description='', public=''):
        """
        Expected data to be sent in a PUT request to the DocumentView
        end point, /documents/<>
        :param name: name of the library to change it to
        :param description: description to change it to

        :return: PUT data in dictionary format
        """
        put_data = dict(
            name=name,
            description=description,
            public=public
        )
        return put_data

    def document_view_put_data_json(self, name='', description='', public=''):
        """
        Expected data to be sent in a PUT request to the DocumentView
        end point, /documents/<>
        :param name: name of the library to change it to
        :param description: description to change it to

        :return: PUT data in JSON format
        """
        put_data = self.document_view_put_data(name=name,
                                               description=description,
                                               public=public)
        return json.dumps(put_data)

    @staticmethod
    def user_view_get_response():
        """
        Expected return data from the user view GET end point

        :return: GET data in dictionary format
        """

        expected_types = ['name', 'description', 'id', 'num_documents',
                          'date_created', 'date_last_modified', 'permission',
                          'public', 'num_users']
        return expected_types
