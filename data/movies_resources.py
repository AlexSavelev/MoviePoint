from flask import jsonify
from flask_restful import abort, Resource
import datetime

from data.movies_reqparcer import parser, search_parser

from data.db_session import create_session
from data.movies import Movies


def abort_if_movie_not_found(movies_id):
    session = create_session()
    movie = session.query(Movies).get(movies_id)
    if not movie:
        abort(404, message=f'Movie {movies_id} not found')


class MoviesResource(Resource):
    def get(self, movies_id):
        abort_if_movie_not_found(movies_id)
        session = create_session()
        movie = session.query(Movies).get(movies_id)
        return jsonify({'movie': movie.to_dict()})

    def delete(self, movies_id):
        abort_if_movie_not_found(movies_id)
        session = create_session()
        movie = session.query(Movies).get(movies_id)
        session.delete(movie)
        session.commit()
        return jsonify({'success': 'OK'})


class MoviesListResource(Resource):
    def get(self):
        session = create_session()
        movies = session.query(Movies).all()
        return jsonify({'movies': [item.to_dict() for item in movies]})

    def post(self):
        args = parser.parse_args()
        session = create_session()
        movie = Movies()
        world_release_date = datetime.date.fromisoformat(args['world_release_date']) \
            if 'world_release_date' in args and args['world_release_date'] else None
        movie.publisher, movie.type, movie.title, movie.description, movie.duration, movie.genres, \
            movie.world_release_date = args['publisher'], args['type'], args['title'], args['description'], \
            args['duration'], args['genres'], world_release_date
        session.add(movie)
        session.commit()
        return jsonify({'success': 'OK'})


class MoviesSearch(Resource):
    def post(self):
        args = search_parser.parse_args()
        session = create_session()
        movies = session.query(Movies).filter(Movies.title.ilike(f'%{args["q"]}%')).all()
        return jsonify({'movies': [item.to_dict(only=('id', 'title', 'cover')) for item in movies]})
