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
from sqlalchemy.dialects.postgresql import JSON, ARRAY

db = SQLAlchemy()


class User(db.Model):
    """
    User table
    Foreign-key absolute_uid is the primary key of the user in the user
    database microservice.
    """
    id = db.Column(db.Integer, primary_key=True)
    absolute_uid = db.Column(db.Integer, unique=True)
    # permissions = db.relationship('permissions', backref='user')

    def __repr__(self):
        return '<User {0}, {1}>'\
            .format(self.id, self.absolute_uid)

#
# class Library(db.Model):
#     """
#     Library table
#     This represents a collection of bibcodes, a biblist, and can be thought of
#     much like a bibtex file.
#     """
#
#     id = db.Column(db.Integer, primary_key=True)
#     name = db.Column(db.String(50))
#     biblist = db.Column(ARRAY(db.String(50)))
#     data = db.Column(JSON)
#     permissions = db.relationship('permissions', backref='library')
#
#     def __rep__(self):
#         return '<Library, name: {0}, number of bibcodes: {1}, data keys: {2}>'\
#             .format(self.name, len(self.biblist), self.data.keys())
#
#
# class Permissions(db.Model):
#     """
#     Permissions table
#
#     Logically connects the library and user table. Whereby, a Library belongs to
#     a user, and the user can give permissions to other users to view their
#     libraries.
#     User (1) to Permissions (Many)
#     Library (1) to Permissions (Many)
#     """
#     id = db.Column(db.Integer, primary_key=True)
#     permission = db.Column(db.String(50))
#
#     user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
#     group_id = db.Column(db.Integer, db.ForeignKey('group.id'))
#
#     def __rep__(self):
#         return '<UserGroup, user: {0}, group: {1}, permission: {2}'\
#             .format(self.user_id, self.group_id, self.permission)
