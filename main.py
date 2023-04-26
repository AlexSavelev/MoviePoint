from flask import Flask
from flask import render_template, redirect, send_from_directory, request, session, abort
from flask_restful import abort, Api
from data.db_session import global_init, create_session
import base64
import datetime

from misc import *

from requests import get, post, delete, put
import json

from data import users_resources, genres_resources, movies_resources, reviews_resources
from filesystem import movie_file_system

from data.users import User

from flask_login import LoginManager, login_user, login_required, logout_user
from flask_login.utils import current_user

from forms.user import LoginForm, RegisterForm
from forms.genres import AddGenreForm
from forms.comment import AddCommentForm
from forms.edit import MyNewForm, EditCoverForm, EditImagesForm, EditMovieForm, EditPublishForm, EditSeriesTitleForm, \
    EditSeriesVideoForm, EditSeriesAudioForm, EditSeriesSubsForm

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


@app.route('/favicon.ico')
def favicon():
    return send_from_directory('', 'favicon.ico')


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

    # Filter
    category = request.args.get('w', default='', type=str)
    query_text = request.args.get('q', default='', type=str)
    sort_type = request.args.get('sort', default='', type=str)
    page_index = request.args.get('page', default=1, type=int) - 1

    if category == 'Жанр':
        found_genres = [i['id'] for i in get(f'{SITE_PATH}/api/v1/genres').json()['genres']
                        if i['title'].lower() == query_text.lower()]
        query_text = found_genres[0] if found_genres else query_text

    nf = False
    if query_text:
        medias = get(f'{SITE_PATH}/api/v1/movies/search', json={'q': query_text, 'w': category,
                                                                'must_be_released': True}).json()['movies']
        if not medias:
            nf = True
            medias = get(f'{SITE_PATH}/api/v1/movies/search', json={'must_be_released': True}).json()['movies']
    else:
        medias = get(f'{SITE_PATH}/api/v1/movies/search', json={'must_be_released': True}).json()['movies']

    pages = [i + 1 for i in range(len(medias) // MAX_MOVIE_COUNT + int((len(medias) % MAX_MOVIE_COUNT != 0)))]
    if len(medias) < page_index * MAX_MOVIE_COUNT:
        abort(404)
    medias = medias[page_index * MAX_MOVIE_COUNT:min((page_index + 1) * MAX_MOVIE_COUNT, len(medias))]

    medias = [
        {'title': i['title'],
         'watch_ref': f'/watch/{i["id"]}',
         'cover_ref': make_image_path(i['id'], i['cover']),
         'rating': calculate_avg_rating(get(f'{SITE_PATH}/api/v1/reviews/search',
                                            json={'movie': i['id']}).json()['reviews']),
         } for i in medias]

    # Sorting
    if sort_type == 'По алфавиту':
        medias.sort(key=lambda x: x['title'])
    elif sort_type == 'По рейтингу':
        medias.sort(key=lambda x: -x['rating'])

    sorted_types = ['Выберите...', 'По алфавиту', 'По рейтингу']
    filter_types = ['Название', 'Жанр', 'Режисёр', 'Возраст']
    return render_template('search.html', title='Поиск', not_found=nf, medias=medias, q=query_text, w=category,
                           sort=sort_type, filter_types=filter_types, sorted_type=sorted_types, pages=pages)


@app.route('/genres', methods=['GET', 'POST'])
def genres():
    if check_user_is_not_authorized('/genres'):
        return redirect('/login')

    genres_json = get(f'{SITE_PATH}/api/v1/genres').json()['genres']
    user_is_admin = current_user.id in ADMINS

    form = AddGenreForm()
    if form.validate_on_submit():
        title = form.title.data
        if any([i['title'] == title for i in genres_json]):
            return render_template('genres.html', title='Жанры', genres=genres_json, is_admin=user_is_admin,
                                   form=form, message='Такой жанр уже существует')
        post(f'{SITE_PATH}/api/v1/genres', json={'title': title})
        return redirect('/genres')

    return render_template('genres.html', title='Жанры', genres=genres_json, is_admin=user_is_admin, form=form)


@app.route('/genres/remove/<int:genre_id>')
def genres_remove(genre_id: int):
    if check_user_is_not_authorized(f'/genres/remove/{genre_id}'):
        return redirect('/login')

    if current_user.id not in ADMINS:
        abort(404)

    result = delete(f'{SITE_PATH}/api/v1/genres/{genre_id}')
    if not result:
        return 'Ошибка. Жанр не найден.'
    return redirect('/genres')


@app.route('/static/movies/<string:movie_id>/<string:series_id>/<string:file_name>')
def stream(movie_id, series_id, file_name):
    video_dir = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}'
    return send_from_directory(video_dir, file_name)


@app.route('/static/movies/<string:movie_id>/<string:series_id>/<string:path>/<string:file_name>')
def stream_from_dir(movie_id, series_id, path, file_name):
    video_dir = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/{path}'
    return send_from_directory(video_dir, file_name)


@app.route('/reviews/add/<int:movie_id>', methods=['GET', 'POST'])
def review_add(movie_id):
    if check_user_is_not_authorized('/reviews/add/<int:movie_id>'):
        return redirect('/login')

    movie = get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()

    if 'movie' not in movie:
        abort(404)

    movie = movie['movie']
    movie_title = movie['title']
    is_publisher = movie['publisher'] == current_user.id

    if is_publisher:
        abort(404)

    form = AddCommentForm()
    if form.validate_on_submit():
        post(f'{SITE_PATH}/api/v1/reviews', json={'movie': movie_id,
                                                  'publisher': current_user.id,
                                                  'rating': int(form.rating.data),
                                                  'title': form.title.data,
                                                  'review': form.review.data})
        return redirect(f'/reviews/add/{movie_id}')
    return render_template('write_review.html', title='Комментарий', form=form, movie_title=movie_title)


@app.route('/watch/<int:movie_id>')
def watch(movie_id):
    if check_user_is_not_authorized('/search'):
        return redirect(f'/watch/{movie_id}')
    movie = get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()

    if 'movie' not in movie:
        abort(404)
    movie = movie['movie']
    is_publisher = movie['publisher'] == current_user.id
    is_editor = is_publisher or (current_user.id in ADMINS)
    published = movie['user_released']
    if (not published) and (not is_editor):
        abort(404)

    if movie['type'] == SERIES:
        movie_series = json.loads(movie['series'])['seasons']
        seasons_titles = sorted(movie_series.keys(), key=sort_title_list_key)
        seasons = [
            {'name': season_title,
             'series': [
                 {'name': series_it['title'],
                  'ref': build_master_src(movie_id, series_it['id'])
                  } for series_it in movie_series[season_title] if series_it['release']
             ]
             } for season_title in seasons_titles]
        if f'last_movie_series_{movie_id}' in request.cookies:
            src = request.cookies[f'last_movie_series_{movie_id}']
        else:
            if seasons and seasons[0]['series']:
                src = seasons[0]['series'][0]['ref']
            else:
                src = ''
    else:
        seasons = []
        src = build_master_src(movie_id, '0')
    images = [make_image_path(movie_id, i) for i in movie['images'].split(',') if i]
    movie_title = movie['title']
    additional_css_links = ['/static/css/video-js.css', '/static/css/videojs-http-source-selector.css']

    movie['world_release_date'] = datetime.date.fromisoformat(movie['world_release_date']).strftime('%d/%m/%Y') \
        if movie['world_release_date'] else ''
    movie['genres'] = ', '.join([get(f'{SITE_PATH}/api/v1/genres/{i}').json().
                                get('genre', {}).get('title', '_') for i in movie['genres'].split(',')]) \
        if movie['genres'] else ''
    description = [('Продолжительность', movie['duration'], False), ('Дата выхода', movie['world_release_date'], False),
                   ('Режисёр', movie['director'], True), ('Страна', movie['country'], False),
                   ('Жанры', movie['genres'], True), ('Возрастной рейтинг', movie['age'], True),
                   ('Описание', movie['description'], True)]

    self_review = get(f'{SITE_PATH}/api/v1/reviews/search',
                      json={'movie': movie_id, 'publisher': current_user.id}).json()['reviews']
    reviews = [i for i in get(f'{SITE_PATH}/api/v1/reviews/search', json={'movie': movie_id}).json()['reviews']
               if i['publisher'] != current_user.id][::-1]

    return render_template('watch.html', title=f'Смотреть "{movie_title}"', movie_title=movie_title, movie_id=movie_id,
                           publisher=movie['user']['username'], additional_css_links=additional_css_links,
                           type=movie['type'], seasons=seasons, src=src, images=images, is_editor=is_editor,
                           published=published, description=description, is_publisher=is_publisher,
                           self_review=self_review, reviews=reviews)


@app.route('/my')
def my():
    if check_user_is_not_authorized('/my'):
        return redirect('/login')
    medias = get(f'{SITE_PATH}/api/v1/movies/search', json={
        'must_be_released': False, 'publisher': current_user.id}).json()['movies']
    medias = [
        {'title': i['title'],
         'editor_ref': f'/watch/{i["id"]}',
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
        movie_type = form.type.data
        if movie_type == FULL_LENGTH:
            movie_series = {'seasons': {
                '0': [
                    {'id': '0', 'title': '', 'video': 0, 'audio': [], 'subs': []}
                ]
            }}
        else:
            movie_series = {'seasons': {}}
        mid = post(f'{SITE_PATH}/api/v1/movies', json={'publisher': current_user.id,
                                                       'type': movie_type,
                                                       'title': form.title.data,
                                                       'series': json.dumps(movie_series)}).json()['movie_id']
        movie_file_system.init(mid)
        if movie_type == FULL_LENGTH:
            movie_file_system.init_series(mid, '0')
        return redirect(f'/watch/{mid}')
    return render_template('my_new.html', title='Загрузить', form=form)


@app.route('/edit/<int:movie_id>/data')
def edit_data(movie_id: int):
    if check_user_is_not_authorized(f'/edit/{movie_id}/data'):
        return redirect('/login')

    movie = get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()
    if ('movie' not in movie) or (movie['movie']['publisher'] != current_user.id and current_user.id not in ADMINS):
        abort(404)
    movie = movie['movie']
    if movie['type'] != SERIES:
        return redirect(f'/watch/{movie_id}')

    series = json.loads(movie['series'])
    seasons_titles = sorted(series['seasons'].keys(), key=sort_title_list_key)
    seasons = [(title, series['seasons'][title]) for title in seasons_titles]

    return render_template('edit_data.html', title='Серии', publisher=movie['user']['username'],
                           movie_title=movie['title'], movie_id=movie_id, seasons=seasons)


@app.route('/edit/<int:movie_id>/data/add_series', methods=['GET', 'POST'])
def edit_data_add(movie_id: int):
    if check_user_is_not_authorized(f'/edit/{movie_id}/data/add_series'):
        return redirect('/login')

    movie = get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()
    if ('movie' not in movie) or (movie['movie']['publisher'] != current_user.id and current_user.id not in ADMINS):
        abort(404)
    movie = movie['movie']
    if movie['type'] != SERIES:
        return redirect(f'/watch/{movie_id}')

    series = json.loads(movie['series'])
    seasons_titles = sorted(series['seasons'].keys(), key=sort_title_list_key)

    form = EditSeriesTitleForm()
    if form.validate_on_submit():
        season, title = form.season.data, form.title.data
        season_series_titles = [i['title'] for i in series['seasons'].get(season, [])]
        if title in season_series_titles:
            return render_template('edit_data_series_title.html', title='Добавить серию',
                                   publisher=movie['user']['username'], movie_title=movie['title'],
                                   seasons_titles=seasons_titles, form=form,
                                   message='Серия с таким названием уже существует в данном сезоне')

        series_id = generate_string()
        if season not in series['seasons']:
            series['seasons'][season] = []
        series['seasons'][season].append({
            'id': series_id, 'title': title, 'video': 0, 'audio': [], 'subs': [], 'release': False
        })
        sort_series_list(series['seasons'][season])
        put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json={'series': json.dumps(series)})
        movie_file_system.init_series(movie_id, series_id)

        return redirect(f'/edit/{movie_id}/data/{series_id}')

    return render_template('edit_data_series_title.html', title='Добавить серию', publisher=movie['user']['username'],
                           movie_title=movie['title'], seasons_titles=seasons_titles, form=form)


@app.route('/edit/<int:movie_id>/data/<string:series>')
def edit_data_series(movie_id: int, series: str):
    if check_user_is_not_authorized(f'/edit/{movie_id}/data/{series}'):
        return redirect('/login')

    movie = get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()
    if ('movie' not in movie) or (movie['movie']['publisher'] != current_user.id and current_user.id not in ADMINS):
        abort(404)
    movie = movie['movie']

    season, series_data = find_series_by_id(series, json.loads(movie['series'])['seasons'])
    if not series_data:
        abort(404)

    is_not_series = movie['type'] != SERIES
    return render_template('edit_data_series.html', title='Редактирование серии', publisher=movie['user']['username'],
                           movie_title=movie['title'], movie_id=movie_id, series=series_data, season=season,
                           is_not_series=is_not_series)


@app.route('/edit/<int:movie_id>/data/<string:series>/title', methods=['GET', 'POST'])
def edit_data_series_title(movie_id: int, series: str):
    if check_user_is_not_authorized(f'/edit/{movie_id}/data/{series}/title'):
        return redirect('/login')

    movie = get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()
    if ('movie' not in movie) or (movie['movie']['publisher'] != current_user.id and current_user.id not in ADMINS):
        abort(404)
    movie = movie['movie']
    if movie['type'] != SERIES:
        return redirect(f'/watch/{movie_id}')

    series_json = json.loads(movie['series'])
    seasons_titles = sorted(series_json['seasons'].keys(), key=sort_title_list_key)
    old_season, old_series_data = find_series_by_id(series, series_json['seasons'])
    if not old_series_data:
        abort(404)

    form = EditSeriesTitleForm()
    if form.validate_on_submit():
        season, title = form.season.data, form.title.data
        if season == old_season:
            season_series_titles = [i['title'] for i in series_json['seasons'].get(season, [])
                                    if i['title'] != old_series_data['title']]
        else:
            season_series_titles = [i['title'] for i in series_json['seasons'].get(season, [])]
        if title in season_series_titles:
            return render_template('edit_data_series_title.html', title='Редактировать серию',
                                   publisher=movie['user']['username'], movie_title=movie['title'],
                                   seasons_titles=seasons_titles, form=form, season=season,
                                   message='Серия с таким названием уже существует в данном сезоне')

        # Remove
        series_json['seasons'][old_season].remove(old_series_data)
        if not series_json['seasons'][old_season]:
            series_json['seasons'].pop(old_season)
        # Add
        if season not in series_json['seasons']:
            series_json['seasons'][season] = []
        new_series_data = old_series_data.copy()
        new_series_data['title'] = title
        series_json['seasons'][season].append(new_series_data)
        sort_series_list(series_json['seasons'][season])
        put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json={'series': json.dumps(series_json)})

        return redirect(f'/edit/{movie_id}/data/{series}')

    form.season.data, form.title.data = old_season, old_series_data['title']
    return render_template('edit_data_series_title.html', title='Редактировать серию',
                           publisher=movie['user']['username'], movie_title=movie['title'],
                           seasons_titles=seasons_titles, form=form)


@app.route('/edit/<int:movie_id>/data/<string:series>/video', methods=['GET', 'POST'])
def edit_data_series_video(movie_id: int, series: str):
    if check_user_is_not_authorized(f'/edit/{movie_id}/data/{series}/video'):
        return redirect('/login')

    movie = get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()
    if ('movie' not in movie) or (movie['movie']['publisher'] != current_user.id and current_user.id not in ADMINS):
        abort(404)
    movie = movie['movie']

    if not ENABLE_DATA_LOAD:
        return '<h1>Загрузка файлов за сервер временно приостановлена!</h1>'

    series_json = json.loads(movie['series'])
    season, series_data = find_series_by_id(series, series_json['seasons'])
    if not series_data:
        abort(404)
    if series_data['video'] != 0:
        return redirect(f'/edit/{movie_id}/data/{series}')

    form = EditSeriesVideoForm()
    if form.validate_on_submit():
        data = form.content.data
        codec = form.codec.data
        audio_bitrate = form.audio_bitrate
        audio_lang = form.audio_lang.data

        ext = data.filename.split('.')[-1]
        if ext == 'mkv':
            if audio_lang != 'no' and audio_bitrate < 10:
                return render_template('edit_data_series_video.html', title='Загрузка видео',
                                       publisher=movie['user']['username'],
                                       movie_title=movie['title'], movie_id=movie_id, form=form,
                                       message='Укажите валидный битрейт!')
            mkv_data = {'codec': codec, 'audio_bitrate': audio_bitrate}
        else:
            mkv_data = {}

        if audio_lang == 'no':
            result = movie_file_system.save_video(movie_id, series, ext, data, **mkv_data)
        else:
            result = movie_file_system.save_video_and_audio_channel(movie_id, series, ext, audio_lang, data, **mkv_data)

        if not result:
            return render_template('edit_data_series_video.html', title='Загрузка видео',
                                   publisher=movie['user']['username'],
                                   movie_title=movie['title'], movie_id=movie_id, form=form,
                                   message='Произошла ошибка в обработке файла')

        series_data['video'] = -1
        if audio_lang != 'no':
            series_data['audio'].append({'lang': audio_lang, 'state': -1})
        series_json = change_series_json(season, series, series_data, series_json)
        put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json={'series': json.dumps(series_json)})

        return redirect(f'/edit/{movie_id}/data/{series}')

    return render_template('edit_data_series_video.html', title='Загрузка видео', publisher=movie['user']['username'],
                           movie_title=movie['title'], movie_id=movie_id, form=form)


@app.route('/edit/<int:movie_id>/data/<string:series>/audio', methods=['GET', 'POST'])
def edit_data_series_audio(movie_id: int, series: str):
    if check_user_is_not_authorized(f'/edit/{movie_id}/data/{series}/audio'):
        return redirect('/login')

    movie = get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()
    if ('movie' not in movie) or (movie['movie']['publisher'] != current_user.id and current_user.id not in ADMINS):
        abort(404)
    movie = movie['movie']

    if not ENABLE_DATA_LOAD:
        return '<h1>Загрузка файлов за сервер временно приостановлена!</h1>'

    series_json = json.loads(movie['series'])
    season, series_data = find_series_by_id(series, series_json['seasons'])
    if not series_data:
        abort(404)
    if any([i['state'] == -1 for i in series_data['audio']]) or series_data['video'] != 1:
        return redirect(f'/edit/{movie_id}/data/{series}')

    form = EditSeriesAudioForm()
    if form.validate_on_submit():
        lang, data = form.lang.data, form.content.data
        if lang in [i['lang'] for i in series_data['audio']]:
            return render_template('edit_data_series_audio.html', title='Загрузка аудио',
                                   publisher=movie['user']['username'],
                                   movie_title=movie['title'], movie_id=movie_id, form=form,
                                   message='Аудио дорожка с этим языком уже существует')
        result = movie_file_system.save_audio_channel(movie_id, series, lang, data.filename.split('.')[-1], data)
        if not result:
            return render_template('edit_data_series_audio.html', title='Загрузка аудио',
                                   publisher=movie['user']['username'],
                                   movie_title=movie['title'], movie_id=movie_id, form=form,
                                   message='Произошла ошибка в обработке файла')

        series_data['audio'].append({'lang': lang, 'state': -1})
        series_json = change_series_json(season, series, series_data, series_json)
        put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json={'series': json.dumps(series_json)})

        return redirect(f'/edit/{movie_id}/data/{series}')

    return render_template('edit_data_series_audio.html', title='Загрузка аудио', publisher=movie['user']['username'],
                           movie_title=movie['title'], movie_id=movie_id, form=form)


@app.route('/edit/<int:movie_id>/data/<string:series>/subs', methods=['GET', 'POST'])
def edit_data_series_subs(movie_id: int, series: str):
    if check_user_is_not_authorized(f'/edit/{movie_id}/data/{series}/subs'):
        return redirect('/login')

    movie = get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()
    if ('movie' not in movie) or (movie['movie']['publisher'] != current_user.id and current_user.id not in ADMINS):
        abort(404)
    movie = movie['movie']

    if not ENABLE_DATA_LOAD:
        return '<h1>Загрузка файлов за сервер временно приостановлена!</h1>'

    series_json = json.loads(movie['series'])
    season, series_data = find_series_by_id(series, series_json['seasons'])
    if not series_data:
        abort(404)
    if any([i['state'] == -1 for i in series_data['subs']]) or series_data['video'] != 1:
        return redirect(f'/edit/{movie_id}/data/{series}')

    form = EditSeriesSubsForm()
    if form.validate_on_submit():
        lang, data = form.lang.data, form.content.data
        if lang in [i['lang'] for i in series_data['subs']]:
            return render_template('edit_data_series_subs.html', title='Загрузка субтитров',
                                   publisher=movie['user']['username'],
                                   movie_title=movie['title'], movie_id=movie_id, form=form,
                                   message='Дорожка субтитров с этим языком уже существует')
        result = movie_file_system.save_subtitle_channel(movie_id, series, lang, data.filename.split('.')[-1], data)
        if not result:
            return render_template('edit_data_series_subs.html', title='Загрузка субтитров',
                                   publisher=movie['user']['username'],
                                   movie_title=movie['title'], movie_id=movie_id, form=form,
                                   message='Произошла ошибка в обработке файла')

        series_data['subs'].append({'lang': lang, 'state': -1})
        series_json = change_series_json(season, series, series_data, series_json)
        put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json={'series': json.dumps(series_json)})

        return redirect(f'/edit/{movie_id}/data/{series}')

    return render_template('edit_data_series_subs.html', title='Загрузка субтитров',
                           publisher=movie['user']['username'],  movie_title=movie['title'],
                           movie_id=movie_id, form=form)


@app.route('/edit/<int:movie_id>/data/<string:series>/remove', methods=['GET', 'POST'])
def edit_data_series_remove(movie_id: int, series: str):
    if check_user_is_not_authorized(f'/edit/{movie_id}/data/{series}/remove'):
        return redirect('/login')

    movie = get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()
    if ('movie' not in movie) or (movie['movie']['publisher'] != current_user.id and current_user.id not in ADMINS):
        abort(404)
    movie = movie['movie']
    if movie['type'] != SERIES:
        return redirect(f'/watch/{movie_id}')

    series_json = json.loads(movie['series'])
    season, series_data = find_series_by_id(series, series_json['seasons'])
    if not series_data:
        abort(404)

    for i in range(len(series_json['seasons'][season])):
        if series_json['seasons'][season][i]['id'] == series:
            t = series_json['seasons'][season][i]
            if t['video'] == -1 or any([i['state'] == -1 for i in t['audio']]) or \
                    any([i['state'] == -1 for i in t['subs']]):
                return '<h1>Отказано! В данный момент идет обработка видео!</h1>'
            series_json['seasons'][season].pop(i)
            break
    if not series_json['seasons'][season]:
        series_json['seasons'].pop(season)
    put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json={'series': json.dumps(series_json)})
    if not series_json['seasons']:
        put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json={'user_released': False})
    movie_file_system.remove_series(movie_id, series)

    return redirect(f'/edit/{movie_id}/data')


@app.route('/edit/<int:movie_id>/images', methods=['GET', 'POST'])
def edit_images(movie_id: int):
    if check_user_is_not_authorized(f'/edit/{movie_id}/images'):
        return redirect('/login')

    movie = get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()
    if ('movie' not in movie) or (movie['movie']['publisher'] != current_user.id and current_user.id not in ADMINS):
        abort(404)
    movie = movie['movie']

    cover_ref = make_image_path(movie_id, movie['cover']) if movie['cover'] else '/static/img/no_cover.png'
    image_refs = [{'abs': make_image_path(movie_id, i), 'rel': i} for i in movie['images'].split(',') if i]
    return render_template('edit_images.html', title='Картинки', cover_ref=cover_ref, image_refs=image_refs,
                           publisher=movie['user']['username'], movie_title=movie['title'], movie_id=movie_id)


@app.route('/edit/<int:movie_id>/images/cover', methods=['GET', 'POST'])
def edit_images_cover(movie_id: int):
    if check_user_is_not_authorized(f'/edit/{movie_id}/images/cover'):
        return redirect('/login')

    movie = get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()
    if ('movie' not in movie) or (movie['movie']['publisher'] != current_user.id and current_user.id not in ADMINS):
        abort(404)
    movie = movie['movie']

    if not ENABLE_DATA_LOAD:
        return '<h1>Загрузка файлов за сервер временно приостановлена!</h1>'

    cover_form = EditCoverForm()
    if cover_form.validate_on_submit():
        if movie['cover']:
            movie_file_system.remove_image(movie_id, movie['cover'])
        data = cover_form.content.data
        filename = generate_string() + '.' + data.filename.split('.')[-1]
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
    if ('movie' not in movie) or (movie['movie']['publisher'] != current_user.id and current_user.id not in ADMINS):
        abort(404)
    movie = movie['movie']

    if not ENABLE_DATA_LOAD:
        return '<h1>Загрузка файлов за сервер временно приостановлена!</h1>'

    images_form = EditImagesForm()
    if images_form.validate_on_submit():
        image_lst = movie['images'].split() if movie['images'] else []
        data = images_form.content.data
        for i in data:
            if not i:
                continue
            ext = i.filename.split('.')[-1]
            if ext not in IMAGES or i.filename == ext:
                return render_template('edit_images_load.html', title='Загрузка', publisher=movie['user']['username'],
                                       movie_title=movie['title'], form=images_form, movie_id=movie_id,
                                       message=f'Загружать можно ТОЛЬКО ИЗОБРАЖЕНИЯ форматов {", ".join(IMAGES)}!')
            filename = generate_string() + '.' + ext
            movie_file_system.save_image(movie_id, filename, i)
            image_lst.append(filename)
        put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json={'images': ','.join(image_lst)})
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
    if ('movie' not in movie) or (movie['movie']['publisher'] != current_user.id and current_user.id not in ADMINS):
        abort(404)
    movie = movie['movie']

    image_lst = movie['images'].split(',') if movie['images'] else []
    if filename not in image_lst:
        abort(404)

    image_lst.remove(filename)
    put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json={'images': ','.join(image_lst)})
    movie_file_system.remove_image(movie_id, filename)

    return '<script>window.close();</script>'


@app.route('/edit/<int:movie_id>/info', methods=['GET', 'POST'])
def edit_info(movie_id: int):
    if check_user_is_not_authorized(f'/edit/{movie_id}/info'):
        return redirect('/login')

    movie = get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()
    if ('movie' not in movie) or (movie['movie']['publisher'] != current_user.id and current_user.id not in ADMINS):
        abort(404)
    movie = movie['movie']

    EditMovieForm.update_genres()
    form = EditMovieForm()

    if form.validate_on_submit():
        user_movie_titles = [i['title'] for i in get(f'{SITE_PATH}/api/v1/movies/search', json={
            'must_be_released': False, 'publisher': current_user.id}).json()['movies']]
        if form.title.data in user_movie_titles and form.title.data != movie['title']:
            return render_template('edit_info.html', title='Информация и управление', form=form,
                                   message='Такое название у вас уже используется', movie_title=movie['title'],
                                   publisher=movie['user']['username'], movie_id=movie_id)
        put_data = {
            'title': form.title.data,
            'description': form.description.data,
            'duration': form.duration.data,
            'genres': ','.join(form.genres.data),
            'country': form.country.data,
            'director': form.director.data,
            'age': form.age.data,
            'world_release_date': form.world_release_date.data.isoformat()
        }
        put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json=put_data)
        return redirect(f'/watch/{movie_id}')

    if not form.title.data:
        form.title.data = movie['title']
    if not form.description.data:
        form.description.data = movie['description']
    if not form.duration.data:
        form.duration.data = movie['duration']
    if not form.genres.data:
        form.genres.data = movie['genres'].split(',')
    if not form.country.data:
        form.country.data = movie['country']
    if not form.director.data:
        form.director.data = movie['director']
    if not form.age.data:
        form.age.data = movie['age']
    if not form.world_release_date.data:
        form.world_release_date.data = datetime.date.fromisoformat(movie['world_release_date']) \
            if movie['world_release_date'] else ''

    return render_template('edit_info.html', title='Информация и управление', form=form, movie_title=movie['title'],
                           publisher=movie['user']['username'], movie_id=movie_id)


@app.route('/edit/<int:movie_id>/remove')
def edit_remove(movie_id: int):
    if check_user_is_not_authorized(f'/edit/{movie_id}/remove'):
        return redirect('/login')

    movie = get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()
    if ('movie' not in movie) or (movie['movie']['publisher'] != current_user.id and current_user.id not in ADMINS):
        abort(404)

    delete(f'{SITE_PATH}/api/v1/movies/{movie_id}')
    movie_file_system.remove(movie_id)

    return redirect('/my')


@app.route('/edit/<int:movie_id>/private')
def edit_private(movie_id: int):
    if check_user_is_not_authorized(f'/edit/{movie_id}/private'):
        return redirect('/login')

    movie = get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()
    if ('movie' not in movie) or (movie['movie']['publisher'] != current_user.id and current_user.id not in ADMINS):
        abort(404)

    put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json={'user_released': False})
    return redirect(f'/watch/{movie_id}')


@app.route('/edit/<int:movie_id>/publish', methods=['GET', 'POST'])
def edit_publish(movie_id: int):
    if check_user_is_not_authorized(f'/edit/{movie_id}/publish'):
        return redirect('/login')

    movie = get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()
    if ('movie' not in movie) or (movie['movie']['publisher'] != current_user.id and current_user.id not in ADMINS):
        abort(404)
    movie = movie['movie']

    publish_series, total_series = 0, 0
    for season in json.loads(movie['series'])['seasons'].values():
        total_series += len(season)
        publish_series += sum([int(i['release']) for i in season])
    if movie['type'] == FULL_LENGTH:
        series_verdict = 'Загружено' if publish_series >= 1 else 'Не загружено'
    else:
        series_verdict = f'Готово к публикации {publish_series}/{total_series} (для публикации необходима одна серия)'

    fill_data = [
        ('Описание', 2 if movie['description'] else -2),
        ('Жанры', 2 if movie['genres'] else -2),
        ('Возрастной рейтинг', 2 if movie['age'] else -2),
        ('Режисёр', 2 if movie['director'] else -2),
        ('Обложка', 2 if movie['cover'] else -2),
        ('Фильм' if movie['type'] == FULL_LENGTH else 'Серии', 1 if publish_series >= 1 else 0, series_verdict)
    ]
    can_be_released = all([i[1] == 1 or i[1] == 2 for i in fill_data])

    form = EditPublishForm()
    if form.validate_on_submit():
        if not can_be_released:
            return render_template('edit_publish.html', title='Публикация', form=form, movie_title=movie['title'],
                                   publisher=movie['user']['username'], movie_id=movie_id, data=fill_data,
                                   can_be_released=can_be_released, message='Публикация невозможна!')
        put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json={'user_released': True})
        return redirect(f'/watch/{movie_id}')

    return render_template('edit_publish.html', title='Публикация', form=form, movie_title=movie['title'],
                           publisher=movie['user']['username'], movie_id=movie_id, data=fill_data,
                           can_be_released=can_be_released)


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
