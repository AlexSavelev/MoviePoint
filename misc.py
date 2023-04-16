import random
from config import *


def make_image_path(movie_id, image):
    return f'{MOVIE_PATH}/{movie_id}/img/{image}'


def build_master_src(movie_id, series_id):
    return f'{MOVIE_PATH}/{movie_id}/{series_id}/master.m3u8'


def generate_string(length=25):
    DIGITS = '0123456789'
    LETTERS = 'qwertyuiopasdfghjklzxcvbnm'
    SYMBOLS = LETTERS + LETTERS.upper() + DIGITS
    return ''.join([random.choice(SYMBOLS) for i in range(length)])


def get_lang_full_name(lang: str):
    if lang in LANG_MAP:
        return LANG_MAP[lang][0]
    return 'Undefined'


def is_admin(user_name: str) -> bool:
    return user_name in ADMINS


def find_series_by_id(series: str, seasons: dict) -> tuple:
    for season_title, season_it in seasons.items():
        for i in season_it:
            if i['id'] == series:
                return season_title, i.copy()
    return '', {}


def change_series_json(season: str, series_id: str, new_data: dict, series_json: dict) -> dict:
    for i in range(len(series_json['seasons'][season])):
        if series_json['seasons'][season][i]['id'] == series_id:
            series_json['seasons'][season][i] = new_data
    return series_json
