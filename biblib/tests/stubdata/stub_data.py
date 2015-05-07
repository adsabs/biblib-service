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

    def get_document(self):
        """
        Generate a fake document, e.g., a bibcode

        :return: document in string format
        """

        bibcode = '2015MNRAS...111...1'
        bibcode_payload = {'bibcode': bibcode}

        return bibcode_payload

    def make_stub(self):
        """
        Makes relevant stub data

        :return: stub data for a document
        """
        return self.get_document()


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

        api_id = 1234
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

    def get_library(self):
        """
        Generate and return stub data for a library

        :return: dictionary of library stub data
        """

        stub_library = dict(
            name='Library1',
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

        return self.stub_library, self.stub_user