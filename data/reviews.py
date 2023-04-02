import sqlalchemy
from sqlalchemy import orm

from .db_session import SqlAlchemyBase
from sqlalchemy_serializer import SerializerMixin


class Reviews(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'reviews'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    movie = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('movies.id'))
    publisher = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    rating = sqlalchemy.Column(sqlalchemy.Integer, nullable=False)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    review = sqlalchemy.Column(sqlalchemy.String, nullable=True)

    user = orm.relationship('User')
    movies = orm.relationship('Movies')
