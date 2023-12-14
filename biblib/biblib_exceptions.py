# encoding: utf-8
"""
Service relevant exceptions
"""

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

class BibcodeNotFoundError(Exception):
    """
    Custom exception. Is raised when the bibcode is not found in library.
    """
    def __init__(self, message):
        """
        Constructor
        :param message: error message
        :return: no return
        """
        super(BibcodeNotFoundError, self).__init__(message)
        self.errors = 'The bibcode given was not found in library.'

class DuplicateNoteError(Exception):
    """
    Custom exception. Is raised when bibcode in library already has a note.
    """
    def __init__(self, message):
        """
        Constructor
        :param message: error message
        :return: no return
        """
        super(DuplicateNoteError, self).__init__(message)
        self.errors = 'Note must be unique for given bibcode and library.'
