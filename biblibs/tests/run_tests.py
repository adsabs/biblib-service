#!/usr/bin/env python
"""
Find and run the unit tests
"""

__author__ = 'V. Sudilovsky'
__maintainer__ = 'V. Sudilovsky'
__copyright__ = 'ADS Copyright 2014, 2015'
__version__ = '1.0'
__email__ = 'ads@cfa.harvard.edu'
__status__ = 'Production'
__license__ = 'MIT'

import unittest
import sys

if __name__ == '__main__':
    suite = unittest.TestLoader().discover('functional_tests')
    results = unittest.TextTestRunner(verbosity=3).run(suite)

    if results.errors or results.failures:
        sys.exit(1)
