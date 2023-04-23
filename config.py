HOST = '127.0.0.1'
SETUP_HOST = '0.0.0.0'

PORT = 5000
SITE_PATH = f'http://{HOST}:{PORT}'

MEDIA_DATA_PATH = 'D:\\_Copies\\_HLS_SPLIT'
MOVIE_PATH = '/static/movies'

ENABLE_DATA_LOAD = True

# Movie types:
FULL_LENGTH = 'FL'
SERIES = 'S'

# Languages
LANG_MAP = {'ru': ('Russian', 'Русский'), 'en': ('English', 'Английский')}
# Ages
AGES = ['0+', '6+', '12+', '16+', '18+']
# IMAGES
IMAGES = 'jpg jpe jpeg png gif svg bmp'.split()

with open('admins.txt', 'r') as admin_f:
    ADMINS = [int(i.rstrip('\n')) for i in admin_f.readlines() if i]
