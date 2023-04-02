import sqlalchemy
from sqlalchemy import orm

from .db_session import SqlAlchemyBase
from sqlalchemy_serializer import SerializerMixin


class Movies(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'movies'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    publisher = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    type = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    description = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    duration = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    genres = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    country = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    director = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    age = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    world_release_date = sqlalchemy.Column(sqlalchemy.Date, nullable=True)
    user_released = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    series = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    cover = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    images = sqlalchemy.Column(sqlalchemy.String, nullable=True)

    user = orm.relationship('User')
