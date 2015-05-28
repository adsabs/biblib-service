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
    def __init__(self, message):

        # Call the base class constructor with the parameters it needs
        super(BackendIntegrityError, self).__init__(message)

        # Now for your custom code...
        self.errors = 'The library name already exists for this user'

class PermissionDeniedError(Exception):
    def __init__(self, message):

        # Call the base class constructor with the parameters it needs
        super(PermissionDeniedError, self).__init__(message)

        # Now for your custom code...
        self.errors = 'You do not have permission to do this'
