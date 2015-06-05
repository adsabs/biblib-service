"""
Models use to define the database

The database is not initiated here, but a pointer is created named db. This is
to be passed to the app creator within the Flask blueprint.
"""

import uuid
from datetime import datetime
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.types import TypeDecorator, CHAR


db = SQLAlchemy()


class GUID(TypeDecorator):
    """Platform-independent GUID type.

    Uses Postgresql's UUID type, otherwise uses
    CHAR(32), storing as stringified hex values.

    Taken from http://docs.sqlalchemy.org/en/latest/core/custom_types.html
    ?highlight=guid#backend-agnostic-guid-type

    Does not work if you simply do the following:
    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    as Flask cannot serialise UUIDs correctly.

    """
    impl = CHAR

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(CHAR(32))

    def process_bind_param(self, value, dialect):
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

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            return uuid.UUID(value)


class MutableList(Mutable, list):
    """
    The PostgreSQL type ARRAY cannot be mutated once it is set. This hack is
    written by the author of SQLAlchemy as a solution. For further reading,
    see:
    https://groups.google.com/forum/#!topic/sqlalchemy/ZiDlGJkVTM0
    and
    http://kirang.in/2014/08/09/creating-a-mutable-array-data-type-in-sqlalchemy
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
        Define a remove action
        :param value: value to be removed

        :return: no return
        """

        list.remove(self, value)
        self.changed()

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
                                  backref='user',
                                  cascade='delete')

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
    bibcode = db.Column(MutableList.as_mutable(ARRAY(db.String(50))))
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
