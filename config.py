HOST = '127.0.0.1'
SETUP_HOST = '0.0.0.0'

PORT = 5000
SITE_PATH = f'http://{HOST}:{PORT}'

MEDIA_DATA_PATH = 'D:\\_Copies\\_HLS_SPLIT'
MOVIE_PATH = '/static/movies'

# Movie types:
FULL_LENGTH = 'FL'
SERIES = 'S'

# Languages
LANG_MAP = {'ru': 'Russian', 'en': 'English'}


with open('admins.txt', 'r') as f:
    ADMINS = [int(i.rstrip('\n')) for i in f.readlines() if i]
