from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import JSON, ARRAY

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    absolute_uid = db.Column(db.Integer, unique=True)

    def __repr__(self):
        return '<User {0}>'.format(self.name)


class Library(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    biblist = db.Column(ARRAY(db.String(50)))
    data = db.Column(JSON)
    grouplibraries = db.relationship('grouplibraries', backref='library')

    def __rep__(self):
        return '<Library, name: {0}, number of bibcodes: {1}, data keys: {2}>'\
            .format(self.name, len(self.biblist), self.data.keys())


class Permissions(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    permission = db.Column(db.String(50))

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    group_id = db.Column(db.Integer, db.ForeignKey('group.id'))

    def __rep__(self):
        return '<UserGroup, user: {0}, group: {1}, permission: {2}'\
            .format(self.user_id, self.group_id, self.permission)
