"""
Models use to define the database

The database is not initiated here, but a pointer is created named db. This is
to be passed to the app creator within the Flask blueprint.
"""

import uuid
from utils import uniquify
from datetime import datetime
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import ARRAY, UUID, JSON
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.types import TypeDecorator, CHAR, String


db = SQLAlchemy()


class GUID(TypeDecorator):
    """
    Platform-independent GUID type.

    Uses Postgresql's UUID type, otherwise uses
    CHAR(32), storing as stringified hex values.

    Taken from http://docs.sqlalchemy.org/en/latest/core/custom_types.html
    ?highlight=guid#backend-agnostic-guid-type

    Does not work if you simply do the following:
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    as Flask cannot serialise UUIDs correctly.

    """
    # Refers to the class of type being decorated
    impl = CHAR

    @staticmethod
    def load_dialect_impl(dialect):
        """
        Load the native type for the database type being used
        :param dialect: database type being used

        :return: native type of the database
        """
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    @staticmethod
    def process_bind_param(value, dialect):
        """
        Format the value for insertion in to the database
        :param value: value of interest
        :param dialect: database type

        :return: value cast to type expected
        """
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return '{0:.32x}'.format(uuid.UUID(value))
            else:
                # hexstring
                return '{0:.32x}'.format(value)

    @staticmethod
    def process_result_value(value, dialect):
        """
        Format the value when it is removed from the database
        :param value: value of interest
        :param dialect: database type

        :return: value cast to the type expected
        """
        if value is None:
            return value
        else:
            return uuid.UUID(value)

    @staticmethod
    def compare_against_backend(dialect, conn_type):
        """
        Return True if the types are different,
        False if not, or None to allow the default implementation
        to compare these types
        :param dialect: database type
        :param conn_type: type of the field

        :return: boolean
        """
        if dialect.name == 'postgresql':
            return isinstance(conn_type, UUID)
        else:
            return isinstance(conn_type, String)

class MutableDict(Mutable, dict):
    """
    By default, SQLAlchemy only tracks changes of the value itself, which works
    "as expected" for simple values, such as ints and strings, but not dicts.
    http://stackoverflow.com/questions/25300447/
    using-list-on-postgresql-json-type-with-sqlalchemy
    """

    @classmethod
    def coerce(cls, key, value):
        """
        Convert plain dictionaries to MutableDict.
        """
        if not isinstance(value, MutableDict):
            if isinstance(value, dict):
                return MutableDict(value)

            # this call will raise ValueError
            return Mutable.coerce(key, value)
        else:
            return value

    def __setitem__(self, key, value):
        """
        Detect dictionary set events and emit change events.
        """
        dict.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        """
        Detect dictionary del events and emit change events.
        """
        dict.__delitem__(self, key)
        self.changed()

    def setdefault(self, key, value):
        """
        Detect dictionary setdefault events and emit change events
        """
        dict.setdefault(self, key, value)
        self.changed()

    def pop(self, key, default):
        """
        Detect dictionary pop events and emit change events
        :param key: key to pop
        :param default: default if key does not exist

        :return: the item under the given key
        """
        dict.pop(self, key, default)
        self.changed()

class MutableList(Mutable, list):
    """
    The PostgreSQL type ARRAY cannot be mutated once it is set. This hack is
    written by the author of SQLAlchemy as a solution. For further reading,
    see:

    https://groups.google.com/forum/#!topic/sqlalchemy/ZiDlGJkVTM0

    and

    http://kirang.in/2014/08/09/
    creating-a-mutable-array-data-type-in-sqlalchemy
    """
    def append(self, value):
        """
        Define an append action
        :param value: value to be appended

        :return: no return
        """

        list.append(self, value)
        self.changed()

    def remove(self, value):
        """
        Define a remove action.
        Passes if the value does not exist within the list.

        :param value: value to be removed

        :return: no return
        """

        try:
            list.remove(self, value)
            self.changed()
        except ValueError:
            pass

    def extend(self, value):
        """
        Define an extend action
        :param value: list to extend with

        :return: no return
        """
        list.extend(self, value)
        self.changed()

    def shorten(self, value):
        """
        Define a shorten action. Opposite to extend

        :param value: values to remove

        :return: no return
        """
        for item in value:
            self.remove(item)

    def upsert(self, value):
        """
        Add values that do not exist in the current list
        :param value:
        :return:
        """
        value = uniquify(value)
        value = [item for item in value if item not in list(self)]

        self.extend(value)

    @classmethod
    def coerce(cls, key, value):
        """
        Re-define the coerce. Ensures that a class deriving from Mutable is
        always returned

        :param key:
        :param value:

        :return:
        """
        if not isinstance(value, MutableList):
            if isinstance(value, list):
                return MutableList(value)
            return Mutable.coerce(key, value)
        else:
            return value


class User(db.Model):
    """
    User table
    Foreign-key absolute_uid is the primary key of the user in the user
    database microservice.
    """
    __bind_key__ = 'libraries'
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    absolute_uid = db.Column(db.Integer, unique=True)
    permissions = db.relationship('Permissions',
                                  backref='user')

    def __repr__(self):
        return '<User {0}, {1}>'\
            .format(self.id, self.absolute_uid)


class Library(db.Model):
    """
    Library table
    This represents a collection of bibcodes, a biblist, and can be thought of
    much like a bibtex file.
    """
    __bind_key__ = 'libraries'
    __tablename__ = 'library'
    id = db.Column(GUID, primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(50))
    description = db.Column(db.String(50))
    public = db.Column(db.Boolean)
    # bibcode = db.Column(MutableList.as_mutable(ARRAY(db.String(50))), default=[])
    default_bibcode = {}
    bibcode = db.Column(MutableDict.as_mutable(JSON), default=default_bibcode)
    date_created = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    date_last_modified = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )
    permissions = db.relationship('Permissions',
                                  backref='library',
                                  cascade='delete')

    def __repr__(self):
        return '<Library, library_id: {0} name: {1}, ' \
               'description: {2}, public: {3},' \
               'bibcode: {4}>'\
            .format(self.id,
                    self.name,
                    self.description,
                    self.public,
                    self.bibcode)

    def get_bibcodes(self):
        """
        Returns the bibcodes of the library
        """
        return self.bibcode.keys()

    def add_bibcodes(self, bibcodes):
        """
        Adds a bibcode to the bibcode field, checking if it exists or not. This
        is essentially an upsert action. We only want to add a bibcode if it
        does not exist already.

        Given the way in which bibcodes are stored may change, it seems simpler
        to keep the method of adding/removing in a small wrapper so that only
        one location needs to be modified (or YAGNI?).

        :param bibcodes: list of bibcodes
        """
        [self.bibcode.setdefault(item, {}) for item in bibcodes]

    def remove_bibcodes(self, bibcodes):
        """
        Removes a bibcode(s) from the bibcode field.

        Given the way in which bibcodes are stored may change, it seems simpler
        to keep the method of adding/removing in a small wrapper so that only
        one location needs to be modified (or YAGNI?).

        :param bibcodes: list of bibcodes
        """
        [self.bibcode.pop(key, None) for key in bibcodes]

class Permissions(db.Model):
    """
    Permissions table

    Logically connects the library and user table. Whereby, a Library belongs
    to a user, and the user can give permissions to other users to view their
    libraries.
    User (1) to Permissions (Many)
    Library (1) to Permissions (Many)
    """
    __bind_key__ = 'libraries'
    __tablename__ = 'permissions'
    id = db.Column(db.Integer, primary_key=True)
    read = db.Column(db.Boolean, default=False)
    write = db.Column(db.Boolean, default=False)
    admin = db.Column(db.Boolean, default=False)
    owner = db.Column(db.Boolean, default=False)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    library_id = db.Column(GUID, db.ForeignKey('library.id'))

    def __repr__(self):
        return '<Permissions, user_id: {0}, library_id: {1}, read: {2}, '\
               'write: {3}, admin: {4}, owner: {5}'\
            .format(self.user_id, self.library_id, self.read, self.write,
                    self.admin, self.owner)
