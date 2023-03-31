from flask import jsonify
from flask_restful import abort, Resource

from data.genres_reqparcer import parser

from data.db_session import create_session
from data.genres import Genres


def abort_if_genre_not_found(genres_id):
    session = create_session()
    genre = session.query(Genres).get(genres_id)
    if not genre:
        abort(404, message=f'Movie {genres_id} not found')


class GenresResource(Resource):
    def get(self, genres_id):
        abort_if_genre_not_found(genres_id)
        session = create_session()
        genre = session.query(Genres).get(genres_id)
        return jsonify({'genre': genre.to_dict()})

    def delete(self, genres_id):
        abort_if_genre_not_found(genres_id)
        session = create_session()
        genre = session.query(Genres).get(genres_id)
        session.delete(genre)
        session.commit()
        return jsonify({'success': 'OK'})


class GenresListResource(Resource):
    def get(self):
        session = create_session()
        genres = session.query(Genres).all()
        return jsonify({'genres': [item.to_dict() for item in genres]})

    def post(self):
        args = parser.parse_args()
        session = create_session()
        genre = Genres()
        genre.title = args['title']
        session.add(genre)
        session.commit()
        return jsonify({'success': 'OK'})
