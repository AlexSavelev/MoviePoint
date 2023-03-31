HOST = '127.0.0.1'
PORT = 5000
SITE_PATH = f'http://{HOST}:{PORT}'

MOVIE_PATH = '/static/movies'
IMG_FOLDER_NAME = 'img'


def make_cover_path(mid, cover):
    return f'{MOVIE_PATH}/{mid}/{IMG_FOLDER_NAME}/{cover}'
