import random
from config import *


def make_image_path(movie_id, image):
    return f'{MOVIE_PATH}/{movie_id}/img/{image}'


def build_master_src(movie_id, series_id):
    return f'{MOVIE_PATH}/{movie_id}/{series_id}/master.m3u8'


def generate_file_name(length=25):
    DIGITS = '0123456789'
    LETTERS = 'qwertyuiopasdfghjklzxcvbnm'
    SYMBOLS = LETTERS + LETTERS.upper() + DIGITS
    return ''.join([random.choice(SYMBOLS) for i in range(length)])
