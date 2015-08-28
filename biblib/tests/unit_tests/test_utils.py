"""
Tests the functions within the utils module
"""

import unittest
from biblib.utils import uniquify, assert_unsorted_equal, get_item

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

    def test_asserted_unsorted_equal_matches_equal_list(self):
        """
        Tests that two hashables are correclty matched when unordered
        """
        list_1 = [1, 2, 2, 3, 4, 4]
        list_2 = [2, 1, 4, 3, 2, 4]

        self.assertTrue(assert_unsorted_equal(list_1, list_2))

    def test_asserted_unsorted_notequal_list(self):
        """
        Tests that two hashables are correctly seen to not match
        """
        list_1 = [1, 2, 2, 3, 4, 4]
        list_2 = [1, 2, 3, 4]
        self.assertFalse(assert_unsorted_equal(list_1, list_2))

    def test_get_item_returns_wanted_value(self):
        """
        Tests that the efficient O(N) search for an item from a dictionary in a
        list of dictionaries is behaving as expected.
        """

        list_of_dictionaries = [
            {'key_1': 'item_1'},
            {'key_2': 'item_2'}
        ]

        item_1 = get_item(list_of_dictionaries, 'key_1')
        item_2 = get_item(list_of_dictionaries, 'key_2')

        self.assertEqual(item_1, 'item_1')
        self.assertEqual(item_2, 'item_2')

if __name__ == '__main__':
    unittest.main(verbosity=2)
