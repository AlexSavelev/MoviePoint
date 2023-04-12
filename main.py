from flask import Flask
from flask import render_template, redirect, send_from_directory, request, session, abort
from flask_restful import abort, Api
from data.db_session import global_init, create_session
import base64

from misc import *

from requests import get, post, delete, put
import json

from data import users_resources, genres_resources, movies_resources, reviews_resources
from data import movie_file_system

from data.users import User

from flask_login import LoginManager, login_user, login_required, logout_user
from flask_login.utils import current_user

from forms.user import LoginForm, RegisterForm
from forms.edit import MyNewForm, EditCoverForm, EditImagesForm

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
def not_found(_):
    data = get('https://http.cat/404').content
    img_data = base64.b64encode(data).decode()
    return "<img src='data:image/png;base64," + img_data + "' style='height: 100%;'/>"


@app.errorhandler(400)
def bad_request(_):
    data = get('https://http.cat/400').content
    img_data = base64.b64encode(data).decode()
    return "<img src='data:image/png;base64," + img_data + "' style='height: 100%;'/>"


@app.errorhandler(500)
def server_error(_):
    data = get('https://http.cat/500').content
    img_data = base64.b64encode(data).decode()
    return "<img src='data:image/png;base64," + \
           img_data + \
           "' style='height: 100%;' alt='Internal server error. " \
           "We will be back as soon as the programmer buys new brains.'/>"


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
        medias = get(f'{SITE_PATH}/api/v1/movies/search', json={'q': query_text,
                                                                'must_be_released': True}).json()['movies']
        if not medias:
            nf = True
            medias = get(f'{SITE_PATH}/api/v1/movies/search', json={'must_be_released': True}).json()['movies']
    else:
        medias = get(f'{SITE_PATH}/api/v1/movies/search', json={'must_be_released': True}).json()['movies']
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
    movie = get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()

    if 'movie' not in movie:
        abort(404)
    movie = movie['movie']
    is_editor = (request.args.get('edit', default='', type=str) == 'true' and (movie['publisher'] == current_user.id))
    published = movie['user_released']
    if (not published) and (not is_editor):
        abort(404)

    number_of_episodes = ''
    if movie['type'] == SERIES:
        number_of_episodes = '0'
        movie_series = json.loads(movie['series'])
        seasons = [
            {'name': f'Сезон {season_number}',
             'series': [
                 {'name': f'Серия {series_number}',
                  'ref': build_master_src(movie_id, series_id)
                  } for series_number, series_id in series_dict.items()
             ]
             } for season_number, series_dict in movie_series.items()]
        for season_number, series_dict in movie_series.items():
            for i in series_dict.items():
                number_of_episodes = str(int(number_of_episodes) + 1)
        if f'last_movie_series_{movie_id}' in request.cookies:
            src = request.cookies[f'last_movie_series_{movie_id}']
        else:
            src = seasons[0]['series'][0]['ref']
    else:
        seasons = []
        src = build_master_src(movie_id, '0')
    images = [make_image_path(movie_id, i) for i in movie['images'].split(',') if i]
    movie_title = movie['title']
    additional_css_links = ['/static/css/video-js.css', '/static/css/videojs-http-source-selector.css']
    description = [movie['duration'], movie['world_release_date'], movie['director'], movie['country'],
                   movie['genres'], movie['age'], number_of_episodes, movie['description']]
    strings = ['Продолжительность: ', 'Дата выхода: ', 'Режисёр: ', 'Страна: ', 'Жанры: ',
               'Возрастной рейтинг: ', 'Количество серий: ', 'Описание: ']
    mounth = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября',
             'декабря']
    description[1] = description[1].split('-')[2] + ' ' + mounth[int(description[1].split('-')[1]) - 1] + ' ' \
                     + description[1].split('-')[0]
    description[5] = description[5] + '+'
    lengh = len(description)
    '''lis = description[4].split(',')
    description[4] = ''
    print(lis)
    for i in range(len(lis)):
        description[4] = description[4] + genres_resources.GenresResource.get(int(lis[i]))['genre']
    print(description[4])'''
    return render_template('watch.html', title=f'Смотреть "{movie_title}"', movie_title=movie_title, movie_id=movie_id,
                           publisher=movie['user']['username'], additional_css_links=additional_css_links,
                           seasons=seasons, src=src, images=images, is_editor=is_editor, published=published,
                           description=list(description), strings=strings, lengh=lengh)


@app.route('/my')
def my():
    if check_user_is_not_authorized('/my'):
        return redirect('/login')
    medias = get(f'{SITE_PATH}/api/v1/movies/search', json={
        'must_be_released': False, 'publisher': current_user.id}).json()['movies']
    medias = [
        {'title': i['title'],
         'editor_ref': f'/watch/{i["id"]}?edit=true',
         'cover_ref': make_image_path(i['id'], i['cover']) if i['cover'] else '/static/img/no_cover.png'
         } for i in medias]
    medias.append({
        'title': 'Загрузить',
        'editor_ref': f'/my/new',
        'cover_ref': '/static/img/new_movie.png'
    })
    return render_template('my.html', title='Мои фильмы/сериалы', medias=medias, number_of_loads=len(medias) - 1)


@app.route('/my/new', methods=['GET', 'POST'])
def my_new():
    if check_user_is_not_authorized('/my/new'):
        return redirect('/login')
    form = MyNewForm()
    if form.validate_on_submit():
        user_movie_titles = [i['title'] for i in get(f'{SITE_PATH}/api/v1/movies/search', json={
            'must_be_released': False, 'publisher': current_user.id}).json()['movies']]
        if form.title.data in user_movie_titles:
            return render_template('my_new.html', title='Загрузить', form=form, message='Такое название у вас '
                                                                                        'уже используется')
        mid = post(f'{SITE_PATH}/api/v1/movies', json={'publisher': current_user.id,
                                                       'type': form.type.data,
                                                       'title': form.title.data}).json()['movie_id']
        movie_file_system.init(mid)
        if form.type.data == FULL_LENGTH:
            movie_file_system.init_series(mid, '0')
        return redirect(f'/watch/{mid}?edit=true')
    return render_template('my_new.html', title='Загрузить', form=form)


@app.route('/edit/<int:movie_id>/data')
def edit_data(movie_id: int):
    pass


@app.route('/edit/<int:movie_id>/data/<string:series>')
def edit_data_series(movie_id: int, series: str):
    pass


@app.route('/edit/<int:movie_id>/images', methods=['GET', 'POST'])
def edit_images(movie_id: int):
    if check_user_is_not_authorized(f'/edit/{movie_id}/images'):
        return redirect('/login')

    movie = get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()
    if ('movie' not in movie) or (movie['movie']['publisher'] != current_user.id):
        abort(404)
    movie = movie['movie']

    cover_ref = make_image_path(movie_id, movie['cover']) if movie['cover'] else '/static/img/no_cover.png'
    image_refs = [{'abs': make_image_path(movie_id, i), 'rel': i} for i in movie['images'].split(',')]
    return render_template('edit_images.html', title='Картинки', cover_ref=cover_ref, image_refs=image_refs,
                           publisher=movie['user']['username'], movie_title=movie['title'], movie_id=movie_id)


@app.route('/edit/<int:movie_id>/images/cover', methods=['GET', 'POST'])
def edit_images_cover(movie_id: int):
    if check_user_is_not_authorized(f'/edit/{movie_id}/images/cover'):
        return redirect('/login')

    movie = get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()
    if ('movie' not in movie) or (movie['movie']['publisher'] != current_user.id):
        abort(404)
    movie = movie['movie']

    cover_form = EditCoverForm()
    if cover_form.validate_on_submit():
        if movie['cover']:
            movie_file_system.remove_image(movie_id, movie['cover'])
        data = cover_form.content.data
        filename = generate_file_name() + '.' + data.filename.split('.')[-1]
        movie_file_system.save_image(movie_id, filename, data)
        put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json={'cover': filename})
        return redirect(f'/edit/{movie_id}/images')

    return render_template('edit_images_load.html', title='Загрузка', publisher=movie['user']['username'],
                           movie_title=movie['title'], form=cover_form, movie_id=movie_id)


@app.route('/edit/<int:movie_id>/images/load', methods=['GET', 'POST'])
def edit_images_load(movie_id: int):
    if check_user_is_not_authorized(f'/edit/{movie_id}/images/load'):
        return redirect('/login')

    movie = get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()
    if ('movie' not in movie) or (movie['movie']['publisher'] != current_user.id):
        abort(404)
    movie = movie['movie']

    images_form = EditImagesForm()
    if images_form.validate_on_submit():
        image_lst = movie['images'].split() if movie['images'] else []
        data = images_form.content.data
        for i in data:
            filename = generate_file_name() + '.' + i.filename.split('.')[-1]
            movie_file_system.save_image(movie_id, filename, i)
            image_lst.append(filename)
        put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json={'images': ' '.join(image_lst)})
        return redirect(f'/edit/{movie_id}/images')

    return render_template('edit_images_load.html', title='Загрузка', publisher=movie['user']['username'],
                           movie_title=movie['title'], form=images_form, movie_id=movie_id)


@app.route('/edit/<int:movie_id>/images/remove')
def edit_images_remove(movie_id: int):
    if check_user_is_not_authorized(f'/edit/{movie_id}/images/remove'):
        return redirect('/login')

    filename = request.args.get('i', default='', type=str)
    if not filename:
        abort(404)

    movie = get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()
    if ('movie' not in movie) or (movie['movie']['publisher'] != current_user.id):
        abort(404)
    movie = movie['movie']

    image_lst = movie['images'].split() if movie['images'] else []
    if filename not in image_lst:
        abort(404)

    image_lst.remove(filename)
    put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json={'images': ' '.join(image_lst)})
    movie_file_system.remove_image(movie_id, filename)

    return '<script>window.close();</script>'


@app.route('/edit/<int:movie_id>/info')
def edit_info(movie_id: int):
    pass


@app.route('/edit/<int:movie_id>/remove')
def edit_remove(movie_id: int):
    pass


@app.route('/edit/<int:movie_id>/private')
def edit_private(movie_id: int):
    pass


@app.route('/edit/<int:movie_id>/publish')
def edit_publish(movie_id: int):
    pass


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

    app.run(port=PORT, host=SETUP_HOST, debug=True)
