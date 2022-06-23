"""
Contains useful functions and utilities that are not neccessarily only useful
for this module. But are also used in differing modules insidide the same
project, and so do not belong to anything specific.
"""

from collections import Counter

def get_GET_params(request, types={}):
    """
    Attempt to coerce GET params data into json from request, falling
    back to the raw data if json could not be coerced.
    :param request: flask.request
    :param types: types that the incoming request object must cohere to
    """
    try:
        get_params = request.args.to_dict()
    except:
        get_params = request.args

    return get_params
    
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

solr_query_fields=["abstract", "ack", "aff", "alternate_bicode", "alternate_title", "arxiv_class", "author", \
    "bibcode", "bibgroup", "bibstem", "body", "citation_count", "copyright", "data", "date", "database", "doi", "doctype"\
    "first_author", "grant", "id", "identifier", "indexstamp", "issue", "keyword", "lang", "orcid_pub", "orcid_user", "orcid_other",\
    "page", "property", "pub", "pubdate", "read_count", "title", "vizier", "volume", "year"]