import os
import shutil
import pysubs2
import webvtt
import enzyme
from multiprocessing import Process

from misc import *
from filesystem.ffprobe import FFProbe, FFProbeError

from filesystem import stream_handler
from filesystem import mkv_stream_handler


def init(movie_id: int):
    os.mkdir(f'{MEDIA_DATA_PATH}/{movie_id}')
    os.mkdir(f'{MEDIA_DATA_PATH}/{movie_id}/img')


def remove(movie_id: int):
    shutil.rmtree(f'{MEDIA_DATA_PATH}/{movie_id}')


def init_series(movie_id: int, series_id: str):
    os.mkdir(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}')
    os.mkdir(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/subs')


def remove_series(movie_id: int, series_id: str):
    shutil.rmtree(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}')


def save_image(movie_id: int, filename: str, content):
    content.save(f'{MEDIA_DATA_PATH}/{movie_id}/img/{filename}')


def remove_image(movie_id: int, filename: str):
    os.remove(f'{MEDIA_DATA_PATH}/{movie_id}/img/{filename}')


def save_video(movie_id: int, series_id: str, ext: str, content):  # h264/mp4
    base_video_path = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/src.{ext}'
    content.save(base_video_path)

    try:
        metadata = FFProbe(base_video_path)
        max_height = int(metadata.video[0].height)
        max_bitrate = int(metadata.video[0].bit_rate) // 1000
        if max_height < 300 or max_bitrate < 10:
            raise ValueError
    except (IOError, FFProbeError, ValueError):
        os.remove(base_video_path)
        return False

    streams = build_streams_list(max_height)
    lower_2p_k = [(max_height / i) ** 2 for i in map(lambda x: x[1], streams)]
    bitrates = [int(max_bitrate / k) for k in lower_2p_k]

    for stream in streams:
        os.mkdir(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/stream_{stream[0]}')

    p1 = Process(target=stream_handler.video, args=(movie_id, series_id, ext, base_video_path, streams, bitrates))
    p1.start()

    return True


def save_audio_channel(movie_id: int, series_id: str, lang: str, ext: str, content):  # aac/mp3
    os.mkdir(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/audio_{lang}')

    base_audio_path = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/{lang}.{ext}'
    content.save(base_audio_path)

    try:
        metadata = FFProbe(base_audio_path)
        bitrate = int(metadata.audio[0].bit_rate) // 1000
        if bitrate < 10:
            raise ValueError
    except (IOError, FFProbeError, ValueError):
        return False

    p1 = Process(target=stream_handler.audio, args=(movie_id, series_id, lang, ext, base_audio_path, bitrate))
    p1.start()

    return True


def save_video_and_audio_channel(movie_id: int, series_id: str, ext: str, audio_lang: str, content):
    audio_ext = 'aac'

    base_video_path = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/src.{ext}'
    base_audio_path = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/{audio_lang}.{audio_ext}'
    content.save(base_video_path)

    try:
        metadata = FFProbe(base_video_path)
        max_height = int(metadata.video[0].height)
        max_bitrate = int(metadata.video[0].bit_rate) // 1000
        audio_bitrate = int(metadata.audio[0].bit_rate) // 1000
        if max_height < 300 or max_bitrate < 10 or audio_bitrate < 10:
            raise ValueError
    except (IOError, FFProbeError, ValueError):
        os.remove(base_video_path)
        return False

    streams = build_streams_list(max_height)
    lower_2p_k = [(max_height / i) ** 2 for i in map(lambda x: x[1], streams)]
    bitrates = [int(max_bitrate / k) for k in lower_2p_k]

    os.mkdir(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/audio_{audio_lang}')
    for stream in streams:
        os.mkdir(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/stream_{stream[0]}')

    p1 = Process(target=stream_handler.video_and_audio,
                 args=(movie_id, series_id, ext, base_video_path, streams, bitrates, audio_lang, audio_ext,
                       base_audio_path, audio_bitrate))
    p1.start()

    return True


def save_subtitle_channel(movie_id: int, series_id: str, lang: str, ext: str, content):  # srt/vtt
    base_sub_path = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/subs/{lang}.vtt'

    if ext == 'vtt':
        content.save(base_sub_path)
    else:
        t_sub_path = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/subs/{lang}.{ext}'
        content.save(t_sub_path)
        t = pysubs2.load(t_sub_path, encoding='utf-8')
        t.save(base_sub_path)
        os.remove(t_sub_path)

    length = webvtt.read(base_sub_path).total_length

    p1 = Process(target=stream_handler.subs, args=(movie_id, series_id, lang, length))
    p1.start()

    return True


def parse_mkv_tracks(base_video_path):
    tracks = {
        'video': [],
        'audio': [],
        'subs': []
    }
    try:
        with open(base_video_path, 'rb') as f:
            mkv = enzyme.MKV(f)
        # Video
        t = mkv.video_tracks[0]
        tracks['video'].append({
            'id': t.number - 1,
            'ext': MKV_V_CODECS[t.codec_id],
            'duration': mkv.info.duration.seconds
        })
        # Audio
        for t in mkv.audio_tracks:
            tracks['audio'].append({
                'id': t.number - 1,
                'ext': MKV_A_CODECS[t.codec_id],
                'default': t.default,
                'lang': t.language
            })
        # Subs
        for t in mkv.subtitle_tracks:
            tracks['subs'].append({
                'id': t.number - 1,
                'ext': MKV_S_CODECS[t.codec_id],
                'default': t.default,
                'lang': t.language
            })
    except (IndexError, ValueError, enzyme.Error):
        os.remove(base_video_path)
        return {}

    a_lang = {}
    for lang in [t['lang'] for t in tracks['audio']]:
        if lang not in a_lang:
            a_lang[lang] = 0
        a_lang[lang] += 1
    for i in range(len(tracks['audio']) - 1, -1, -1):
        if a_lang[tracks['audio'][i]['lang']] == 1:
            continue
        tracks['audio'][i]['lang'] += ('_' + str(a_lang[tracks['audio'][i]['lang']]))
        tracks['audio'][i]['lang'] -= 1

    a_lang = {}
    for lang in [t['lang'] for t in tracks['subs']]:
        if lang not in a_lang:
            a_lang[lang] = 0
        a_lang[lang] += 1
    for i in range(len(tracks['subs']) - 1, -1, -1):
        if a_lang[tracks['subs'][i]['lang']] == 1:
            continue
        tracks['subs'][i]['lang'] += ('_' + str(a_lang[tracks['subs'][i]['lang']]))
        tracks['subs'][i]['lang'] -= 1

    tracks['audio'].sort(key=lambda x: -int(x['default']))
    tracks['subs'].sort(key=lambda x: -int(x['default']))

    return tracks


def save_mkv(movie_id: int, series_id: str, content):
    base_video_path = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/src.mkv'
    content.save(base_video_path)

    tracks = parse_mkv_tracks(base_video_path)
    if not tracks:
        return False

    p1 = Process(target=mkv_stream_handler.mkv, args=(movie_id, series_id, tracks))
    p1.start()
    return True
