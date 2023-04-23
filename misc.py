import random
from config import *


def make_image_path(movie_id, image):
    return f'/static/movies/{movie_id}/img/{image}'


def build_master_src(movie_id, series_id):
    return f'/static/movies/{movie_id}/{series_id}/master.m3u8'


def generate_string(length=25):
    DIGITS = '0123456789'
    LETTERS = 'qwertyuiopasdfghjklzxcvbnm'
    SYMBOLS = LETTERS + LETTERS.upper() + DIGITS
    return ''.join([random.choice(SYMBOLS) for i in range(length)])


def sort_title_list_key(key) -> list:
    import re

    def convert(text):
        return int(text) if text.isdigit() else text

    return [convert(c) for c in re.split('([0-9]+)', key)]


def sort_series_list(series_list: list[dict]) -> None:
    import re

    def convert(text):
        return int(text) if text.isdigit() else text

    def alphanum_key(key):
        return [convert(c) for c in re.split('([0-9]+)', key['title'])]

    series_list.sort(key=alphanum_key)


def get_lang_full_name(lang: str):
    if lang in LANG_MAP:
        return LANG_MAP[lang][0]
    return 'Undefined'


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


def calculate_avg_rating(ratings: list[dict]) -> float:
    if not ratings:
        return 0.0
    return round(sum([i['rating'] for i in ratings]) / len(ratings), 2)


def build_streams_list(height: int) -> list[tuple]:
    if height not in RESOLUTIONS:
        return [(i, int(height / k)) for i, k in enumerate([1, 1.5, 2.25, 2.25 * 1.333333])]
    return [(i, s) for i, s in enumerate(RESOLUTIONS[RESOLUTIONS.index(height):])]
