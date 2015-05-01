from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON, ARRAY

from app import create_app

app = create_app()
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    absolute_uid = db.Column(db.Integer, unique=True)

    def __repr__(self):
        return '<User {0}>'.format(self.name)


class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    usergroup = db.relationship('usergroup', backref='group')
    grouplibraries = db.relationship('grouplibraries', backref='group')

    def __repr__(self):
        return '<Group {0}>'.format(self.name)


class UserGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    permission = db.Column(db.String(50))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))

    def __rep__(self):
        return '<UserGroup, user: {0}, group: {1}, permission: {2}'\
            .format(self.user_id, self.group_id, self.permission)


class Library(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    biblist = db.Column(ARRAY(db.String(50)))
    data = db.Column(JSON)
    grouplibraries = db.relationship('grouplibraries', backref='library')
    
    def __rep__(self):
        return '<Library, name: {0}, number of bibcodes: {1}, data keys: {2}>'\
            .format(self.name, len(self.biblist), self.data.keys())


class GroupLibraries(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    library_id = db.Column(db.Integer, db.ForeignKey('library.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))

    def __repr__(self):
        return '<GroupLibraries, library: {0}, group: {1}'\
            .format(self.library_id, self.group_id)