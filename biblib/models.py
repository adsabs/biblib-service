"""
Models use to define the database

The database is not initiated here, but a pointer is created named db. This is
to be passed to the app creator within the Flask blueprint.
"""

__author__ = 'J. Elliott'
__maintainer__ = 'J. Elliott'
__copyright__ = 'ADS Copyright 2015'
__version__ = '1.0'
__email__ = 'ads@cfa.harvard.edu'
__status__ = 'Production'
__license__ = 'MIT'

from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.ext.mutable import Mutable

db = SQLAlchemy()


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
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    absolute_uid = db.Column(db.Integer, unique=True)
    permissions = db.relationship('Permissions', backref='user')

    def __repr__(self):
        return '<User {0}, {1}>'\
            .format(self.id, self.absolute_uid)


class Library(db.Model):
    """
    Library table
    This represents a collection of bibcodes, a biblist, and can be thought of
    much like a bibtex file.
    """
    __tablename__ = 'library'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    description = db.Column(db.String(50))
    public = db.Column(db.Boolean)
    bibcode = db.Column(MutableList.as_mutable(ARRAY(db.String(50))))
    permissions = db.relationship('Permissions', backref='library')

    def __repr__(self):
        return '<Library, library_id: {0:d} name: {1}, ' \
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
    __tablename__ = 'permissions'
    id = db.Column(db.Integer, primary_key=True)
    read = db.Column(db.Boolean)
    write = db.Column(db.Boolean)

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    library_id = db.Column(db.Integer, db.ForeignKey('library.id'))

    def __repr__(self):
        return '<Permissions, user_id: {0}, library_id: {1}, read: {2}, '\
               'write: {3}'\
            .format(self.user_id, self.library_id, self.read, self.write)
