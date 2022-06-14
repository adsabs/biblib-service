"""
Place holder for the views. The current views file would be too large and can
get annoying to scroll when reading the source code.
"""
# Constant definitions
DEFAULT_LIBRARY_NAME_PREFIX = 'Untitled Library'
DEFAULT_LIBRARY_DESCRIPTION = 'My ADS library'
USER_ID_KEYWORD = 'X-Adsws-Uid'

from .base_view import BaseView
from .user_view import UserView
from .library_view import LibraryView
from .document_view import DocumentView
from .document_view import QueryView
from .permission_view import PermissionView
from .transfer_view import TransferView
from .classic_view import ClassicView, TwoPointOhView
from .operations_view import OperationsView