"""
Tests the functions within the utils module
"""

import sys
import os

PROJECT_HOME = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../'))
sys.path.append(PROJECT_HOME)


import unittest
from utils import uniquify

class TestUtils(unittest.TestCase):
    """
    Class for testing the behaviour of the custom functions in the utils module
    """

    def test_uniquify_removes_duplication(self):
        """
        Tests the uniquify function that uniques the items in a list

        :return: no return
        """

        non_unique_list = [1, 1, 2, 2, 3, 3, 4, 4]
        unique_list = [1, 2, 3, 4]
        uniqued_list = uniquify(non_unique_list)

        # Ensure one value
        for item in unique_list:
            values = [i for i in uniqued_list if i == item]
            self.assertEqual(1, len(values))

    def test_uniquify_preserves(self):
        """
        Tests the uniquify function that uniques the items in a list

        :return: no return
        """

        non_unique_list = [2, 2, 1, 1, 3, 3, 4, 4]
        unique_list = [2, 1, 3, 4]
        uniqued_list = uniquify(non_unique_list)

        for i in range(len(unique_list)):
            self.assertEqual(unique_list[i], uniqued_list[i])

if __name__ == '__main__':
    unittest.main(verbosity=2)