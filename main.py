from flask import Flask
from flask import render_template, redirect, abort, make_response, jsonify, request, session
from flask_restful import reqparse, abort, Api, Resource
from data.db_session import global_init, create_session

from config import *

from requests import get, post, delete, put

from data import users_resources, genres_resources, movies_resources

from data.users import User
from data.genres import Genres
from data.movies import Movies

from flask_login import LoginManager, login_user, login_required, logout_user
from flask_login.utils import current_user

from forms.user import LoginForm, RegisterForm

app = Flask(__name__)
api = Api(app)
app.config['SECRET_KEY'] = 'nRLhAQWy'
login_manager = LoginManager()
login_manager.init_app(app)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.errorhandler(400)
def bad_request(_):
    return make_response(jsonify({'error': 'Bad Request'}), 400)


@app.errorhandler(500)
def server_error(_):
    return make_response(jsonify(
        {'error': "Internal server error. We'll be back as soon as the programmer buys new brains."}), 400)


def check_user_is_not_authorized(page='/'):
    if current_user and current_user.is_authenticated:
        return False
    session['after_auth_url'] = page
    return True


@login_manager.user_loader
def load_user(user_id):
    return create_session().query(User).get(user_id)


@app.route('/')
def index():
    return render_template('index.html', title='Movie Point')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db_sess.query(User).filter(User.username == form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            if 'after_auth_url' in session:
                return redirect(session.pop('after_auth_url'))
            return redirect('/')
        return render_template('login.html', message='Неправильный логин или пароль', form=form)
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация', form=form, message='Пароли не совпадают')
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация', form=form,
                                   message='Пользователь с таким email уже есть')
        if db_sess.query(User).filter(User.username == form.username.data).first():
            return render_template('register.html', title='Регистрация', form=form,
                                   message='Пользователь с таким логином уже есть')
        user = User()
        user.username, user.email = form.username.data, form.email.data
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        login_user(user, remember=form.remember_me.data)
        if 'after_auth_url' in session:
            return redirect(session.pop('after_auth_url'))
        return redirect('/')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/search')
def search():
    if check_user_is_not_authorized('/search'):
        return redirect('/login')
    query_text = request.args.get('q', default='', type=str)
    nf = False
    if query_text:
        medias = post(f'{SITE_PATH}/api/v1/movies/search', json={'q': query_text}).json()['movies']
        if not medias:
            nf = True
            medias = get(f'{SITE_PATH}/api/v1/movies').json()['movies']
    else:
        medias = get(f'{SITE_PATH}/api/v1/movies').json()['movies']
    medias = [
        {'title': i['title'],
         'watch_ref': f'/watch/{i["id"]}',
         'cover_ref': make_cover_path(i['id'], i['cover'])
         } for i in medias]
    return render_template('search.html', title='Поиск', not_found=nf, medias=medias)


if __name__ == '__main__':
    global_init('db/movie_point.db')
    db_sess = create_session()

    api.add_resource(users_resources.UsersListResource, '/api/v1/users')
    api.add_resource(users_resources.UsersResource, '/api/v1/users/<int:users_id>')
    api.add_resource(genres_resources.GenresListResource, '/api/v1/genres')
    api.add_resource(genres_resources.GenresResource, '/api/v1/genres/<int:genres_id>')
    api.add_resource(movies_resources.MoviesListResource, '/api/v1/movies')
    api.add_resource(movies_resources.MoviesResource, '/api/v1/movies/<int:movies_id>')
    api.add_resource(movies_resources.MoviesSearch, '/api/v1/movies/search')

    app.run(port=PORT, host=HOST)
