from flask import jsonify
from flask_restful import abort, Resource

from data.reviews_reqparcer import parser, search_parser

from data.db_session import create_session
from data.reviews import Reviews


def abort_if_review_not_found(rev_id):
    session = create_session()
    rev = session.query(Reviews).get(rev_id)
    if not rev:
        abort(404, message=f'Review {rev_id} not found')


class ReviewsResource(Resource):
    def get(self, rev_id):
        abort_if_review_not_found(rev_id)
        rev = create_session().query(Reviews).get(rev_id)
        return jsonify({'review': rev.to_dict()})

    def delete(self, rev_id):
        abort_if_review_not_found(rev_id)
        session = create_session()
        rev = session.query(Reviews).get(rev_id)
        session.delete(rev)
        session.commit()
        return jsonify({'success': 'OK'})


class ReviewsListResource(Resource):
    def get(self):
        revs = create_session().query(Reviews).all()
        return jsonify({'reviews': [item.to_dict() for item in revs]})

    def post(self):
        args = parser.parse_args()
        session = create_session()
        rev = Reviews()
        rev.movie, rev.publisher, rev.rating, rev.title, rev.review = args['movie'], args['publisher'], \
            args['rating'], args['title'], args['review']
        session.add(rev)
        session.commit()
        return jsonify({'success': 'OK'})


class ReviewsSearch(Resource):
    def get(self):
        args = search_parser.parse_args()
        if args['publisher']:
            revs = create_session().query(Reviews).filter(Reviews.movie == args['movie'],
                                                          Reviews.publisher == args['publisher']).all()
        else:
            revs = create_session().query(Reviews).filter(Reviews.movie == args['movie']).all()
        return jsonify({'reviews': [item.to_dict() for item in revs]})
