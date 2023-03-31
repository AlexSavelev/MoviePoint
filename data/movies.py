import sqlalchemy
from sqlalchemy import orm

from .db_session import SqlAlchemyBase
from sqlalchemy_serializer import SerializerMixin


class Movies(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'movies'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    publisher = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    title = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    description = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    duration_min = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    genres = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    world_release_date = sqlalchemy.Column(sqlalchemy.Date, nullable=True)
    user_released = sqlalchemy.Column(sqlalchemy.Boolean, default=False)

    user = orm.relationship('User')
