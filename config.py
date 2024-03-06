from configparser import ConfigParser
from pathlib import Path


HOST = '127.0.0.1'
SETUP_HOST = '0.0.0.0'

PORT = 5000
SITE_PATH = f'http://{HOST}:{PORT}'

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
# MKV Codecs
MKV_V_CODECS = {
    'V_MPEG4/ISO/AVC': 'h264',
    'V_MPEGH/ISO/HEVC': 'h265',
    'V_MS/VFW/FOURCC': 'avi',
    'V_QUICKTIME': 'mov',
    'V_MPEG2': '.mpg'
}
MKV_A_CODECS = {
    'A_MPEG': 'mp3',
    'A_MPEG/L3': 'mp3',
    'A_PCM': 'pcm',
    'A_TRUEHD': 'ac3',
    'A_PCM/INT/BIG': 'pcm',
    'A_PCM/INT/LIT': 'pcm',
    'A_PCM/FLOAT/IEEE': 'pcm',
    'A_MPC': 'mpc',
    'A_AC3': 'ac3',  # BEST
    'A_EAC3': 'eac3',  # BEST
    'A_AC3/BSID9': 'ac3',
    'A_AC3/BSID10': 'ac3',
    'A_ALAC': 'alac',
    'A_DTS': 'dts',
    'A_DTS/LOSSLESS': 'dts',
    'A_VORBIS': 'ogg',
    'A_FLAC': 'flac',  # BEST
    'A_MS/ACM': 'acm',
    'A_AAC': 'aac',  # BEST
    'A_AAC/MPEG2/MAIN': 'aac',  # BEST
    'A_AAC/MPEG2/LC': 'aac',  # BEST
    'A_AAC/MPEG2/LC/SBR': 'aac',  # BEST
    'A_AAC/MPEG2/SSR': 'aac',  # BEST
    'A_AAC/MPEG4/MAIN': 'aac',  # BEST
    'A_AAC/MPEG4/LC': 'aac',  # BEST
    'A_AAC/MPEG4/LC/SBR': 'aac',  # BEST
    'A_AAC/MPEG4/SSR': 'aac',  # BEST
    'A_AAC/MPEG4/LTP': 'aac',  # BEST
    'A_QUICKTIME': 'm4a',
    'A_WAV': 'wav',
    'A_OPUS': 'ogg',
    'A_WAVPACK4': 'wav'  # BEST
}
MKV_S_CODECS = {
    'S_TEXT/UTF8': 'txt',
    'S_TEXT/SSA': 'ssa',
    'S_TEXT/ASS': 'ass',  # BEST
    'S_TEXT/WEBVTT': 'vtt'  # BEST
}

with open('admins.txt', 'r') as admin_f:
    ADMINS = [int(i.rstrip('\n')) for i in admin_f.readlines() if i]


# Server.ini
config = ConfigParser()
config.read('server.ini')
if 'MEDIA_DATA' in config and 'EnableDataLoad' in config['MEDIA_DATA'] and 'MediaDataPath' in config['MEDIA_DATA']:
    ENABLE_DATA_LOAD = (config['MEDIA_DATA']['EnableDataLoad'].lstrip('"').rstrip('"') == 'true')
    MEDIA_DATA_PATH = config['MEDIA_DATA']['MediaDataPath'].lstrip('"').rstrip('"')
else:
    print('No MEDIA_DATA in server.ini configuration file. Set default value')
    ENABLE_DATA_LOAD = False
    MEDIA_DATA_PATH = str(Path(__file__).parent.resolve())
if 'FlaskApp' in config and 'SecretKey' in config['FlaskApp']:
    SECRET_KEY = config['FlaskApp']['SecretKey'].lstrip('"').rstrip('"')
else:
    print('No FlaskApp in server.ini configuration file. Set default value')
    SECRET_KEY = 'X9s1X'
del config
