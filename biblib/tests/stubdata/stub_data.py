"""
Contains stub data that is to be used within the tests to avoid DRY
"""

__author__ = 'J. Elliott'
__maintainer__ = 'J. Elliott'
__copyright__ = 'ADS Copyright 2015'
__version__ = '1.0'
__email__ = 'ads@cfa.harvard.edu'
__status__ = 'Production'
__credit__ = ['V. Sudilovsky']
__license__ = 'MIT'

import random


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
            read=True,
            write=True,
            public=True
        )

        return stub_library

    def make_stub(self):
        """
        Make stub data which contains a user and a library

        :return: stub library and user
        """

        self.stub_library = self.get_library()
        self.stub_user = StubDataUser().get_user()

        self.libraries.append([self.get_library(), StubDataUser().get_user()])

        return self.libraries[-1]