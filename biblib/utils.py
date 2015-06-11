"""
Contains useful functions and utilities that are not neccessarily only useful
for this module. But are also used in differing modules insidide the same
project, and so do not belong to anything specific.
"""

def get_post_data(request):
    """
    Attempt to coerce POST json data from the request, falling
    back to the raw data if json could not be coerced.
    :type request: flask.request
    """
    try:
        return request.get_json(force=True)
    except:
        return request.values


class BackendIntegrityError(Exception):
    """
    Custom exception that is raised when there are application errors similar
    to those seen on the database side. Similar to the IntegrityError that
    can be raised by SQLAlchemy.
    """
    def __init__(self, message):
        """
        Constructor
        :param message: error message
        :return: no return
        """
        super(BackendIntegrityError, self).__init__(message)
        self.errors = 'The library name already exists for this user'

class PermissionDeniedError(Exception):
    """
    Custom exception. Is raised when a user does not have permission to carry
    out a specific action.
    """
    def __init__(self, message):
        """
        Constructor
        :param message: error message
        :return: no return
        """
        super(PermissionDeniedError, self).__init__(message)
        self.errors = 'You do not have permission to do this'
