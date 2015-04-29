"""
Client
"""

__author__ = 'V. Sudilovsky'
__maintainer__ = 'V. Sudilovsky'
__copyright__ = 'ADS Copyright 2014, 2015'
__version__ = '1.0'
__email__ = 'ads@cfa.harvard.edu'
__status__ = 'Production'
__license__ = 'MIT'

import requests


class Client:
    """
    The Client class is a thin wrapper around requests; Use it as a centralized
    place to set application specific parameters, such as the oauth2
    authorization header
    """
    def __init__(self, client_config, send_oauth2_token=True):
        """
        Constructor

        :param client_config: configuration dictionary of the client
        :param send_oauth2_token: should the app send the oauth token
        :return: no return
        """

        self.config = client_config
        self.session = requests.Session()

        if send_oauth2_token:
            # Better to raise KeyError than default to an unusable token
            self.token = self.config['TOKEN']

            self.session.headers.update(
                {'Authorization': 'Bearer %s' % self.token}
            )