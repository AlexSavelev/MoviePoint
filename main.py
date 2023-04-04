from flask import Flask
from flask import render_template, redirect, send_from_directory, make_response, jsonify, request, session, abort
from flask_restful import reqparse, abort, Api, Resource
from data.db_session import global_init, create_session

from config import *
from misc import *

from requests import get, post, delete, put
import json

from data import users_resources, genres_resources, movies_resources, reviews_resources

from data.users import User
from data.genres import Genres
from data.movies import Movies
from data.reviews import Reviews

from flask_login import LoginManager, login_user, login_required, logout_user
from flask_login.utils import current_user

from forms.user import LoginForm, RegisterForm

app = Flask(__name__)
api = Api(app)
app.config['SECRET_KEY'] = 'nRLhAQWy'
login_manager = LoginManager()
login_manager.init_app(app)


@app.after_request
def add_header(response):
    response.headers['X-UA-Compatible'] = 'IE=Edge,chrome=1'
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


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
        db_sess = create_session()
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
        db_sess = create_session()
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
        medias = post(f'{SITE_PATH}/api/v1/movies/search', json={'q': query_text,
                                                                 'must_be_released': True}).json()['movies']
        if not medias:
            nf = True
            medias = get(f'{SITE_PATH}/api/v1/movies').json()['movies']
    else:
        medias = get(f'{SITE_PATH}/api/v1/movies').json()['movies']
    medias = [
        {'title': i['title'],
         'watch_ref': f'/watch/{i["id"]}',
         'cover_ref': make_image_path(i['id'], i['cover'])
         } for i in medias]
    return render_template('search.html', title='Поиск', not_found=nf, medias=medias, q=query_text)


@app.route('/static/movies/<string:movie_id>/<string:series_id>/<string:file_name>')
def stream(movie_id, series_id, file_name):
    video_dir = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}'
    return send_from_directory(video_dir, file_name)


@app.route('/static/movies/<string:movie_id>/<string:series_id>/<string:path>/<string:file_name>')
def stream_from_dir(movie_id, series_id, path, file_name):
    video_dir = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/{path}'
    return send_from_directory(video_dir, file_name)


@app.route('/watch/<int:movie_id>')
def watch(movie_id):
    if check_user_is_not_authorized('/search'):
        return redirect(f'/watch/{movie_id}')
    db_sess = create_session()
    movie = db_sess.query(Movies).get(movie_id)
    if not movie:
        abort(404)
    if movie.type == SERIES:
        movie_series = json.loads(movie.series)
        seasons = [
            {'name': f'Сезон {season_number}',
             'series': [
                 {'name': f'Серия {series_number}',
                  'ref': build_master_src(movie_id, series_id)
                  } for series_number, series_id in series_dict.items()
             ]
             } for season_number, series_dict in movie_series.items()]
        if f'last_movie_series_{movie_id}' in request.cookies:
            src = request.cookies[f'last_movie_series_{movie_id}']
        else:
            src = seasons[0]['series'][0]['ref']
    else:
        seasons = []
        src = build_master_src(movie_id, '0')
    images = [make_image_path(movie_id, i) for i in movie.images.split(',')]
    additional_css_links = ['/static/css/video-js.css', '/static/css/videojs-http-source-selector.css']
    return render_template('watch.html', title=f'Смотреть "{movie.title}"', movie_title=movie.title, movie_id=movie_id,
                           publisher=movie.user.username, additional_css_links=additional_css_links, seasons=seasons,
                           src=src, images=images)


@app.route('/my')
def my():
    if check_user_is_not_authorized('/my'):
        return redirect('/login')
    medias = post(f'{SITE_PATH}/api/v1/movies/search', json={
        'q': '', 'must_be_released': True, 'publisher': current_user.id}).json()['movies']
    medias = [
        {'title': i['title'],
         'editor_ref': f'/my/edit/{i["id"]}',
         'cover_ref': make_image_path(i['id'], i['cover'])
         } for i in medias]
    medias.append({
        'title': 'Добавить',
        'editor_ref': f'/my/new',
        'cover_ref': '/static/img/'
    })
    return render_template('my.html', title='Мои фильмы/сериалы', medias=medias)


if __name__ == '__main__':
    global_init('db/movie_point.db')
    api.add_resource(users_resources.UsersListResource, '/api/v1/users')
    api.add_resource(users_resources.UsersResource, '/api/v1/users/<int:users_id>')
    api.add_resource(genres_resources.GenresListResource, '/api/v1/genres')
    api.add_resource(genres_resources.GenresResource, '/api/v1/genres/<int:genres_id>')
    api.add_resource(movies_resources.MoviesListResource, '/api/v1/movies')
    api.add_resource(movies_resources.MoviesResource, '/api/v1/movies/<int:movies_id>')
    api.add_resource(movies_resources.MoviesSearch, '/api/v1/movies/search')
    api.add_resource(reviews_resources.ReviewsListResource, '/api/v1/reviews')
    api.add_resource(reviews_resources.ReviewsResource, '/api/v1/reviews/<int:rev_id>')
    api.add_resource(reviews_resources.ReviewsSearch, '/api/v1/reviews/search')

    app.run(port=PORT, host=HOST)
