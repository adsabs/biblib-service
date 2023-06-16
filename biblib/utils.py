"""
Contains useful functions and utilities that are not neccessarily only useful
for this module. But are also used in differing modules insidide the same
project, and so do not belong to anything specific.
"""

from collections import Counter
import json

def get_GET_params(request, types={}):
    """
    Attempt to coerce GET params data into json from request, falling
    back to the raw data if json could not be coerced.
    :param request: flask.request
    :param types: types that the incoming request object must cohere to
    """
    try:
        get_params = request.args.to_dict()
    except ValueError:
        msg = "Failed to parse input parameters: {}. Please confirm request is properly formatted.".format(request)
        raise ValueError(msg)
    if "q" in get_params.keys():
        return get_params
    else:
        msg = "Query: {} is missing parameter 'q'. Please confirm request conforms to ADS /search syntax.".format(get_params)
        raise ValueError(msg)

def get_post_data(request, types={}):
    """
    Attempt to coerce POST json data from the request, falling
    back to the raw data if json could not be coerced.
    :param request: flask.request
    :param types: types that the incoming request object must cohere to
    """
    try:
        post_data = request.get_json(force=True)
    except:
        post_data = request.values

    if types and isinstance(post_data, dict):
        for expected_key in types:
            if expected_key not in post_data.keys():
                continue

            if not isinstance(post_data[expected_key],
                              types[expected_key]):
                raise TypeError(
                    '{0} should be type {1} but is {2}'
                    .format(expected_key,
                            types[expected_key],
                            type(post_data[expected_key]))
                )

    return post_data

def err(error_dictionary):
    """
    Formats the error response as wanted by the Flask app
    :param error_dictionary: name of the error dictionary

    :return: tuple of error message and error number
    """
    return {'error': error_dictionary['body']}, error_dictionary['number']

def uniquify(input_list):
    """
    Finds the unique values in a list. This keeps the order of the list, as
    opposed to the standard list(set()) method.

    Adopted from: http://stackoverflow.com/
    questions/
    480214/
    how-do-you-remove-duplicates-from-a-list-in-python-whilst-preserving-order
    :param input_list: list that can contain duplicates

    :return: same ordered list without duplications
    """
    seen = set()
    seen_add = seen.add
    return [item for item in input_list if not (item in seen or seen_add(item))]


def assert_unsorted_equal(s, t):
    """
    Given two hashable types that are not sorted, this checks if the same number
    of values are present in both.
    :param s: first hashable item
    :param t: second hashable item
    :return: Equal (True) / Not equal (False)
    """
    return Counter(s) == Counter(t)

def get_item(list_of_dictionaries, key):
    """
    Given a list of dictionaries, it returns the first dictionary that
    contains the given key, and the item for that key.
    :param list_of_dictionaries: list(dict())
    :param key: key of dictionary wanted

    :return: contents of list(dict[key])
    """
    return next(
        item[key]for item in list_of_dictionaries if key in item.keys()
    )

def check_boolean(value):
    if str(value).lower() not in ['true', 'false']: 
        raise ValueError
    else:
        #safe way to convert string to boolean
        return json.loads(value.lower())