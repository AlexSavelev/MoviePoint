from flask import jsonify
from flask_restful import abort, Resource

from data.users_reqparcer import parser

from data.db_session import create_session
from data.users import User


def abort_if_users_not_found(users_id):
    session = create_session()
    users = session.query(User).get(users_id)
    if not users:
        abort(404, message=f'User {users_id} not found')


class UsersResource(Resource):
    def get(self, users_id):
        abort_if_users_not_found(users_id)
        session = create_session()
        user = session.query(User).get(users_id)
        return jsonify({'user': user.to_dict()})

    def delete(self, users_id):
        abort_if_users_not_found(users_id)
        session = create_session()
        user = session.query(User).get(users_id)
        session.delete(user)
        session.commit()
        return jsonify({'success': 'OK'})


class UsersListResource(Resource):
    def get(self):
        session = create_session()
        users = session.query(User).all()
        return jsonify({'users': [item.to_dict() for item in users]})

    def post(self):
        args = parser.parse_args()
        session = create_session()
        users = User()
        users.username, users.email, users.hashed_password = args['username'], args['email'], args['hashed_password']
        session.add(users)
        session.commit()
        return jsonify({'success': 'OK'})
