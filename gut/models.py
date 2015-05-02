from sqlalchemy import create_engine, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import sessionmaker, relationship, backref

engine = create_engine('sqlite:///:memory:', echo=True)

Base = declarative_base()

Session = sessionmaker(bind=engine)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    user_uid = Column(Integer)

    def __repr__(self):
        return '<User(user_uid={0})>'.format(
            self.user_uid
        )


class Library(Base):
    __tablename__ = 'library'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))

    user = relationship('User', backref=backref('library', order_by=id))

    def __repr__(self):
        return '<Library(id={0}, user_id={1})>'.format(
            self.id, self.user_uid
        )


class Group(Base):
    __tablename__ = 'group'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))

    user = relationship('User')

Base.metadata.create_all(engine)


ed_user = User(user_uid=1234)
session = Session()
session.add(ed_user)
# session.commit()
our_user = session.query(User).filter_by(user_uid=1234).first()
print(our_user)