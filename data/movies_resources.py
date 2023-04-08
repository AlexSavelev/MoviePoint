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

    def put(self, movies_id):
        abort_if_movie_not_found(movies_id)
        args = {i: j for i, j in parser.parse_args().items() if j is not None}
        session = create_session()
        session.query(Movies).filter(Movies.id == movies_id).update(args)
        session.commit()
        return jsonify({'success': 'OK'})

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

        movie.publisher, movie.type, movie.title = args['publisher'], args['type'], args['title']
        movie.description = args['description'] if args['description'] else ''
        movie.duration = args['duration'] if args['duration'] else ''
        movie.genres = args['genres'] if args['genres'] else ''
        movie.country = args['country'] if args['country'] else ''
        movie.director = args['director'] if args['director'] else ''
        movie.age = args['age'] if args['age'] else ''
        movie.world_release_date = datetime.date.fromisoformat(args['world_release_date']) \
            if 'world_release_date' in args and args['world_release_date'] else None
        movie.user_released = args['user_released'] if args['user_released'] else False
        movie.series = args['series'] if args['series'] else ''
        movie.cover = args['cover'] if args['cover'] else ''
        movie.images = args['images'] if args['images'] else ''

        session.add(movie)
        session.commit()
        return jsonify({'success': 'OK', 'movie_id': movie.id})


class MoviesSearch(Resource):
    def get(self):
        args = search_parser.parse_args()
        q = args['q'].lower() if args['q'] is not None else ''
        must_be_released = args['must_be_released'] if args['must_be_released'] is not None else False
        publisher = args['publisher'] if args['publisher'] is not None else 0
        session = create_session()
        # movies = session.query(Movies).filter(Movies.title.ilike(f'%{args["q"].lower()}%')).all()
        movies = []
        for i in session.query(Movies).all():
            if (not must_be_released or i.user_released) and \
                    (q in i.title.lower()) and \
                    (publisher == 0 or i.publisher == publisher):
                movies.append(i)
        return jsonify({'movies': [item.to_dict(only=('id', 'title', 'cover')) for item in movies]})
