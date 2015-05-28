"""
Contains stub data that is to be used within the tests to avoid DRY
"""

import random
import json
import factory
from faker import Faker
from models import User, Library
from views import USER_ID_KEYWORD

faker = Faker()

def fake_biblist(nb_codes):

    bibcodes = []
    for i in range(nb_codes):
        year = faker.year()
        author = faker.random_letter().upper()
        provider = 3*author
        bibcode = '{year}.....{provider}......{author}'\
            .format(year=year,
                    provider=provider,
                    author=author)
        bibcodes.append(bibcode)

    return bibcodes[0]

class UserFactory(factory.Factory):
    class Meta:
        model = User

    id = factory.Sequence(lambda n: n)
    absolute_uid = factory.LazyAttribute(lambda x: faker.random_int())
    email = factory.LazyAttribute(lambda x: faker.email())
    # permissions

class LibraryFactory(factory.Factory):
    class Meta:
        model = Library
    name = factory.LazyAttribute(lambda x: faker.sentence(nb_words=3)[:49])
    description = \
        factory.LazyAttribute(lambda x: faker.sentence(nb_words=5)[:49])
    public = False
    read = False
    write = False
    bibcode = factory.LazyAttribute(lambda x: fake_biblist(nb_codes=1))

class UserShop(object):

    def __init__(self):

        self.stub = UserFactory.stub()
        self.headers = {}

        for key in self.stub.__dict__.keys():
            setattr(self, key, self.stub.__dict__[key])

        self.create_header()

    def create_header(self):
        self.headers = {USER_ID_KEYWORD: self.absolute_uid}

    def permission_view_post_data(self, permission, value):

        post_data = dict(
            email=self.email,
            permission=permission,
            value=value
        )

        return post_data

    def permission_view_post_data_json(self, permission, value):

        post_data = self.permission_view_post_data(permission, value)
        return json.dumps(post_data)

class LibraryShop(object):
    """
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

    """

    def __init__(self):

        self.stub = LibraryFactory.stub()

        self.user_view_post_data = None
        self.user_view_post_data_json = None

        for key in self.stub.__dict__.keys():
            setattr(self, key, self.stub.__dict__[key])

        self.create_user_view_post_data()

    def create_user_view_post_data(self):

        post_data = dict(
            name=self.name,
            description=self.description,
            read=False,
            write=False,
            public=False
        )

        json_data = json.dumps(post_data)

        self.user_view_post_data = post_data
        self.user_view_post_data_json = json_data

    def document_view_post_data(self, action='add'):

        post_data = dict(
            bibcode=self.bibcode,
            action=action
        )
        return post_data

    def document_view_post_data_json(self, action='add'):

        post_data = self.document_view_post_data(action)
        return json.dumps(post_data)


class StubDataDocument(object):
    """
    Generator class for creating and returning stub data for testing the
    users. It may be over kill currently, but I foresee its use will grow.
    """

    def __init__(self):
        """
        Class constructor

        :return: no return
        """

        self.name = 'Stub Data for User'
        self.documents = []

    def get_document(self, **kwargs):
        """
        Generate a fake document, e.g., a bibcode
        :param kwargs: list of kwargs that will go into the output dictionary

        :return: document in string format
        """

        year = '200{0}'.format(int(random.random()*9.0))
        _id = (random.random()*99)+100
        bibcode = '{year}MNRAS...{id}...J'.format(year=year,
                                                  id=_id)
        bibcode_payload = {'bibcode': bibcode}

        for key in kwargs:
            bibcode_payload[key] = kwargs[key]

        return bibcode_payload

    def make_stub(self, **kwargs):
        """
        Makes relevant stub data
        :param kwargs: key word parameters to go in the outgoing document

        :return: stub data for a document
        """

        new_document = self.get_document(**kwargs)
        self.documents.append(new_document)

        return new_document


class StubDataUser(object):
    """
    Generator class for creating and returning stub data for testing the
    users. It may be over kill currently, but I foresee its use will grow.
    """

    def __init__(self):
        """
        Class constructor

        :return: no return
        """

        self.name = 'Stub Data for User'

    def get_user(self):

        api_id = int(random.random()*1000)
        return api_id


class StubDataLibrary(object):
    """
    Generator class for creating and returning stub data for testing the
    libraries. It may be over kill currently, but I foresee its use will grow.
    """

    def __init__(self):
        """
        Class constructor

        :return: no return
        """

        self.name = 'Stub Data for Libraries'
        self.stub_user = None
        self.stub_library = None
        self.libraries = []

    def get_library(self):
        """
        Generate and return stub data for a library

        :return: dictionary of library stub data
        """

        list_of_words = ['My', 'Library', 'first', 'second',
                         'science', 'astronomy', 'word']

        def random_word():
            """Return a random word"""
            return list_of_words[int((random.random()*len(list_of_words)))-1]

        jumble = " ".join([random_word() for i in range(3)])

        current_names = [j['name'] for j in zip(*self.libraries)]
        while jumble in current_names:
            jumble += random_word()

        stub_library = dict(
            name=jumble,
            description='My first library',
            read=False,
            write=False,
            public=False
        )

        return stub_library

    def make_stub(self):
        """
        Make stub data which contains a user and a library

        :return: stub library and user
        """

        self.stub_library = self.get_library()
        self.stub_user = StubDataUser().get_user()

        self.libraries.append([self.stub_library, self.stub_user])

        return self.libraries[-1]