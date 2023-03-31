import sqlalchemy
from sqlalchemy import orm

from .db_session import SqlAlchemyBase
from sqlalchemy_serializer import SerializerMixin


class Series(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'series'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    publisher = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))
    name = sqlalchemy.Column(sqlalchemy.String, nullable=False, default='series_{}')
    title = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    description = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    duration_seasons = sqlalchemy.Column(sqlalchemy.Integer)
    duration_series = sqlalchemy.Column(sqlalchemy.Integer)
    genres = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    world_release_date = sqlalchemy.Column(sqlalchemy.Date, nullable=True)
    user_released = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    series = sqlalchemy.Column(sqlalchemy.String, nullable=True)

    user = orm.relationship('User')
