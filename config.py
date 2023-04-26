HOST = '127.0.0.1'
SETUP_HOST = '0.0.0.0'

PORT = 5000
SITE_PATH = f'http://{HOST}:{PORT}'

ENABLE_DATA_LOAD = True
MEDIA_DATA_PATH = 'D:\\_Copies\\_HLS_SPLIT'

# Movie types
FULL_LENGTH = 'FL'
SERIES = 'S'

MAX_MOVIE_COUNT = 20

# Languages
LANG_MAP = {
    'ru': ('Russian', 'Русский'),
    'en': ('English', 'Английский'),
    'fr': ('French', 'Француский'),
    'ja': ('Japanese', 'Японский'),
    'zh': ('Chinese', 'Китайский')
}
# Ages
AGES = ['0+', '6+', '12+', '16+', '18+']
# IMAGES
IMAGES = ['jpg', 'jpe', 'jpeg', 'png', 'gif', 'svg', 'bmp']
# Resolutions
RESOLUTIONS = [4320, 2160, 1440, 1080, 720, 480, 360]
# Codecs
CODECS = ['h264/aac', 'h264/flac', 'h264/other', 'h265', 'hvc', 'xc']

with open('admins.txt', 'r') as admin_f:
    ADMINS = [int(i.rstrip('\n')) for i in admin_f.readlines() if i]
