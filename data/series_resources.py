from flask import jsonify
from flask_restful import abort, Resource
import datetime

from data.series_reqparcer import parser

from data.db_session import create_session
from data.series import Series


def abort_if_series_not_found(series_id):
    session = create_session()
    series = session.query(Series).get(series_id)
    if not series:
        abort(404, message=f'Movie {series_id} not found')


class SeriesResource(Resource):
    def get(self, series_id):
        abort_if_series_not_found(series_id)
        session = create_session()
        series = session.query(Series).get(series_id)
        return jsonify({'series': series.to_dict()})

    def delete(self, series_id):
        abort_if_series_not_found(series_id)
        session = create_session()
        series = session.query(Series).get(series_id)
        session.delete(series)
        session.commit()
        return jsonify({'success': 'OK'})


class SeriesListResource(Resource):
    def get(self):
        session = create_session()
        series = session.query(Series).all()
        return jsonify({'series': [item.to_dict() for item in series]})

    def post(self):
        args = parser.parse_args()
        session = create_session()
        series = Series()
        world_release_date = datetime.date.fromisoformat(args['world_release_date']) \
            if 'world_release_date' in args and args['world_release_date'] else None
        series.publisher, series.title, series.description, series.duration_seasons, series.duration_series, \
            series.genres, series.world_release_date, series.user_released = args['publisher'], args['title'], \
            args['description'], args['duration_seasons'], args['duration_series'], args['genres'], \
            world_release_date, args['user_released']
        session.add(series)
        session.commit()
        return jsonify({'success': 'OK'})
