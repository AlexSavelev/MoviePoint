import os
import subprocess
from misc import *


class cd:
    """Context manager for changing the current working directory"""
    def __init__(self, newPath):
        self.newPath = os.path.expanduser(newPath)

    def __enter__(self):
        self.savedPath = os.getcwd()
        os.chdir(self.newPath)

    def __exit__(self, etype, value, traceback):
        os.chdir(self.savedPath)


def init(movie_id: int):
    os.mkdir(f'{MEDIA_DATA_PATH}/{movie_id}')
    os.mkdir(f'{MEDIA_DATA_PATH}/{movie_id}/img')


def init_series(movie_id: int, series_id: str):
    os.mkdir(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}')


def save_image(movie_id: int, filename: str, content):
    content.save(f'{MEDIA_DATA_PATH}/{movie_id}/img/{filename}')


def remove_image(movie_id: int, filename: str):
    os.remove(f'{MEDIA_DATA_PATH}/{movie_id}/img/{filename}')


def save_audio_channel(movie_id: int, series_id: str, lang: str, ext: str, bitrate: int, content):  # aac/mp3
    os.mkdir(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/audio_{lang}')
    base_audio_path = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/{lang}.{ext}'

    with open(base_audio_path, 'wb') as f:
        f.write(content)

    with cd(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}'):
        command = f'"../../ffmpeg.exe" -y -i "{lang}.{ext}" -c:a aac -b:a {bitrate}k -muxdelay 0 -f segment ' \
                  f'-sc_threshold 0 -segment_time 2 -segment_list "a_{lang}.m3u8" ' \
                  f'-segment_format mpegts "audio_{lang}/data%%04d.ts"'
        result = subprocess.call(command, shell=True)

    if result != 0:
        os.remove(base_audio_path)
        os.remove(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/audio_{lang}')
        os.remove(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/a_{lang}.m3u8')

    return result == 0


def save_video(movie_id: int, series_id: str, ext: str, max_bitrate: int, max_height: int, content):  # h264/mp4
    for stream in [0, 1, 2, 3]:
        os.mkdir(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/stream_{stream}')

    lower_k = [1, 1.5, 2.25, 2.25 * 1.333333]
    scales = [int(max_height / k) for k in lower_k]
    bitrates = [int(max_bitrate / k) for k in lower_k]

    base_video_path = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/src.{ext}'
    with open(base_video_path, 'wb') as f:
        f.write(content)

    with cd(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}'):
        command = f'"../../ffmpeg.exe" -y -i src.{ext} -hls_time 8 -hls_list_size 0 -filter:v:0 scale=-2:{scales[0]} ' \
                  f'-filter:v:1 scale=-2:{scales[1]} -filter:v:2 scale=-2:{scales[2]} ' \
                  f'-filter:v:3 scale=-2:{scales[3]} -b:v:0 {bitrates[0]}k -b:v:1 {bitrates[1]}k ' \
                  f'-b:v:2 {bitrates[2]}k -b:v:3 {bitrates[3]}k -map 0:v -map 0:v -map 0:v -map 0:v ' \
                  f'-var_stream_map "v:0 v:1 v:2 v:3" -master_pl_name master.m3u8 ' \
                  f'-hls_segment_filename stream_%%v/data%%04d.ts stream_%%v.m3u8'
        result = subprocess.call(command, shell=True)

    if result != 0:
        os.remove(base_video_path)
        os.remove(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/master.m3u8')
        for stream in [0, 1, 2, 3]:
            os.remove(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/stream_{stream}')
            os.remove(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/stream_{stream}.m3u8')

    return result == 0
