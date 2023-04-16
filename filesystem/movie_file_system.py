import os
import subprocess
import shutil
import webvtt
from multiprocessing import Process

from misc import *
from filesystem.ffprobe import FFProbe
from filesystem import stream_handler


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
    for stream in [0, 1, 2, 3]:
        os.mkdir(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/stream_{stream}')

    base_video_path = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/src.{ext}'
    content.save(base_video_path)

    try:
        metadata = FFProbe(base_video_path)
        max_height = int(metadata.video[0].height)
        max_bitrate = int(metadata.video[0].bit_rate) // 1000
        if max_height < 100 or max_bitrate < 10:
            raise ValueError
    except:
        return False

    lower_k = [1, 1.5, 2.25, 2.25 * 1.333333]
    scales = [int(max_height / k) for k in lower_k]
    bitrates = [int(max_bitrate / k) for k in lower_k]

    p1 = Process(target=stream_handler.video, args=(movie_id, series_id, ext, base_video_path, scales, bitrates))
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
    except:
        return False

    p1 = Process(target=stream_handler.audio, args=(movie_id, series_id, lang, ext, base_audio_path, bitrate))
    p1.start()

    return True


def save_subtitle_channel(movie_id: int, series_id: str, lang: str, ext: str, content):  # srt/vtt
    base_sub_path = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/subs/{lang}.vtt'

    if ext == 'vtt':
        content.save(base_sub_path)
    elif ext == 'srt':
        t_sub_path = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/subs/{lang}.srt'
        content.save(t_sub_path)
        t = webvtt.from_srt(t_sub_path)
        t.save(base_sub_path)
        os.remove(t_sub_path)
    else:
        return False

    length = webvtt.read(base_sub_path).total_length

    p1 = Process(target=stream_handler.subs, args=(movie_id, series_id, lang, length))
    p1.start()

    return True
