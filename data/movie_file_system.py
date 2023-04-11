import os
import subprocess
import shutil
import webvtt
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


def replace_ts_dirs(file_path: str, r_from: str, r_to: str):
    with open(file_path, 'r') as f:
        data = f.read().replace(r_from, r_to)
    with open(file_path, 'w') as f:
        f.write(data)


def add_media_param(master_path: str, param):
    with open(master_path, 'r') as f:
        data = f.readlines()
    index = data.index('#EXT-X-VERSION:3') + 1
    data.insert(index, param)
    with open(master_path, 'w') as f:
        f.writelines(data)


def add_param_to_streams(master_path: str, param: str):
    with open(master_path, 'r') as f:
        data = f.readlines()
    for index in [i for i, line in enumerate(data) if line.startswith('#EXT-X-STREAM-INF')]:
        data[index] += param
    with open(master_path, 'w') as f:
        f.writelines(data)


def save_audio_channel(movie_id: int, series_id: str, lang: str, ext: str, bitrate: int,
                       content, add_to_streams=False):  # aac/mp3
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
        shutil.rmtree(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/audio_{lang}')
        try:
            os.remove(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/a_{lang}.m3u8')
        except OSError:
            pass
        return False

    replace_ts_dirs(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/a_{lang}.m3u8', 'data', f'audio_{lang}/data')

    master_path = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/master.m3u8'
    if add_to_streams:
        add_param_to_streams(master_path, f',AUDIO="stereo"')
    param = f'#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="stereo",LANGUAGE="{lang}",NAME="{get_lang_full_name(lang)}",' \
            f'DEFAULT={"YES" if lang == "ru" else "NO"},AUTOSELECT=YES,URI="a_{lang}.m3u8"'
    add_media_param(master_path, param)

    return True


def save_subtitle_channel(movie_id: int, series_id: str, lang: str, ext: str,
                          content, add_to_streams=False):  # srt/vtt
    base_sub_path = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/subs/{lang}.vtt'

    if ext == 'vtt':
        with open(base_sub_path, 'w') as f:
            f.write(content)
    elif ext == 'srt':
        t_sub_path = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/subs/{lang}.srt'
        with open(t_sub_path, 'w') as f:
            f.write(content)
        t = webvtt.from_srt(t_sub_path)
        t.save(base_sub_path)
        os.remove(t_sub_path)
    else:
        return False

    length = webvtt.read(base_sub_path).total_length
    m3u8_data = f"#EXTM3U\n#EXT-X-TARGETDURATION:{length}\n#EXT-X-VERSION:3\n#EXT-X-MEDIA-SEQUENCE:1\n" \
                f"#EXT-X-PLAYLIST-TYPE:VOD\n#EXTINF:{length}.0,\nsubs/{lang}.vtt\n#EXT-X-ENDLIST"

    with open(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/s_{lang}.m3u8', 'w') as f:
        f.write(m3u8_data)

    master_path = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/master.m3u8'
    if add_to_streams:
        add_param_to_streams(master_path, f',SUBTITLES="subs"')
    param = f'#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="{get_lang_full_name(lang)}",' \
            f'DEFAULT={"YES" if lang == "ru" else "NO"},AUTOSELECT=YES,FORCED=NO,LANGUAGE="{lang}",URI="s_{lang}.m3u8"'
    add_media_param(master_path, param)

    return True


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
        try:
            os.remove(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/master.m3u8')
        except OSError:
            pass
        for stream in [0, 1, 2, 3]:
            shutil.rmtree(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/stream_{stream}')
            try:
                os.remove(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/stream_{stream}.m3u8')
            except OSError:
                pass
        return False

    for stream in [0, 1, 2, 3]:
        replace_ts_dirs(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/stream_{stream}.m3u8',
                        'data', f'stream_{stream}/data')

    return True
