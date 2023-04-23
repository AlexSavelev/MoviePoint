import os
import subprocess
import shutil
from requests import get, put
import json

from misc import *


def replace_ts_dirs(file_path: str, r_from: str, r_to: str):
    with open(file_path, 'r') as f:
        data = f.read().replace(r_from, r_to)
    with open(file_path, 'w') as f:
        f.write(data)


def add_media_param(master_path: str, param):
    with open(master_path, 'r') as f:
        data = f.readlines()
    index = data.index('#EXT-X-VERSION:3\n') + 1
    data.insert(index, param)
    with open(master_path, 'w') as f:
        f.writelines(data)


def add_param_to_streams(master_path: str, param: str):
    with open(master_path, 'r') as f:
        data = f.readlines()
    for index in [i for i, line in enumerate(data) if line.startswith('#EXT-X-STREAM-INF')]:
        data[index] = data[index].rstrip('\n') + param + '\n'
    with open(master_path, 'w') as f:
        f.writelines(data)


def video(movie_id, series_id, ext, base_video_path, streams, bitrates):
    series_json = json.loads(get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()['movie']['series'])
    season, series_data = find_series_by_id(series_id, series_json['seasons'])

    print(f'[video handler] starting with streams: {streams} and bitrates {bitrates}')

    command = f'"../../ffmpeg" -y -i src.{ext} -hls_time 8 -hls_list_size 0 ' \
              f'{" ".join([f"-filter:v:{stream[0]} scale=-2:{stream[1]}" for stream in streams])} ' \
              f'{" ".join([f"-b:v:{stream[0]} {b}k" for stream, b in zip(streams, bitrates)])} ' \
              f'{" ".join([f"-map 0:v"] * len(streams))} ' \
              f'-var_stream_map "{" ".join([f"v:{stream[0]}" for stream in streams])}" -master_pl_name master.m3u8 ' \
              f'-hls_segment_filename stream_%%v/data%%04d.ts stream_%%v.m3u8'
    bat_dir = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}'
    bat_path = f'{bat_dir}/v.bat'
    with open(bat_path, 'w') as f:
        f.write(command)
    p = subprocess.Popen(bat_path, shell=True, stdout=subprocess.PIPE, cwd=bat_dir)
    stdout, stderr = p.communicate()
    result = p.returncode
    os.remove(bat_path)

    print(f'[video handler] exit code {result}')
    if result != 0:
        os.remove(base_video_path)
        try:
            os.remove(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/master.m3u8')
        except OSError:
            pass
        for stream in streams:
            shutil.rmtree(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/stream_{stream[0]}')
            try:
                os.remove(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/stream_{stream[0]}.m3u8')
            except OSError:
                pass

        series_data['video'] = 0
        series_json = change_series_json(season, series_id, series_data, series_json)
        put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json={'series': json.dumps(series_json)})
        return False

    for stream in streams:
        replace_ts_dirs(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/stream_{stream[0]}.m3u8',
                        'data', f'stream_{stream[0]}/data')

    series_data['video'] = 1
    series_json = change_series_json(season, series_id, series_data, series_json)
    put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json={'series': json.dumps(series_json)})
    return True


def audio(movie_id, series_id, lang, ext, base_audio_path, bitrate):
    series_json = json.loads(get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()['movie']['series'])
    season, series_data = find_series_by_id(series_id, series_json['seasons'])
    is_first_audio = len(series_data['audio']) == 1

    command = f'"../../ffmpeg" -y -i "{lang}.{ext}" -c:a aac -b:a {bitrate}k -muxdelay 0 -f segment ' \
              f'-sc_threshold 0 -segment_time 2 -segment_list "a_{lang}.m3u8" ' \
              f'-segment_format mpegts "audio_{lang}/data%%04d.ts"'
    bat_dir = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}'
    bat_path = f'{bat_dir}/a_{lang}.bat'
    with open(bat_path, 'w') as f:
        f.write(command)
    p = subprocess.Popen(bat_path, shell=True, stdout=subprocess.PIPE, cwd=bat_dir)
    stdout, stderr = p.communicate()
    result = p.returncode
    os.remove(bat_path)

    if result != 0:
        os.remove(base_audio_path)
        shutil.rmtree(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/audio_{lang}')
        try:
            os.remove(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/a_{lang}.m3u8')
        except OSError:
            pass

        for i in range(len(series_data['audio'])):
            if series_data['audio'][i]['lang'] == lang:
                series_data['audio'].pop(i)
                break
        series_json = change_series_json(season, series_id, series_data, series_json)
        put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json={'series': json.dumps(series_json)})
        return False

    replace_ts_dirs(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/a_{lang}.m3u8', 'data', f'audio_{lang}/data')

    master_path = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/master.m3u8'
    if is_first_audio:
        add_param_to_streams(master_path, f',AUDIO="stereo"')
    param = f'#EXT-X-MEDIA:TYPE=AUDIO,GROUP-ID="stereo",LANGUAGE="{lang}",NAME="{get_lang_full_name(lang)}",' \
            f'DEFAULT={"YES" if is_first_audio else "NO"},AUTOSELECT=YES,URI="a_{lang}.m3u8"\n\n'
    add_media_param(master_path, param)

    for i in range(len(series_data['audio'])):
        if series_data['audio'][i]['lang'] == lang:
            series_data['audio'][i]['state'] = 1
            break
    series_data['release'] = True
    series_json = change_series_json(season, series_id, series_data, series_json)
    put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json={'series': json.dumps(series_json)})
    return True


def video_and_audio(movie_id, series_id, ext, base_video_path, streams, bitrates,
                    audio_lang, audio_ext, base_audio_path, audio_bitrate):
    vr = video(movie_id, series_id, ext, base_video_path, streams, bitrates)
    if not vr:
        return False

    command = f'"../../ffmpeg" -i src.{ext} -vn -acodec copy "{audio_lang}.{audio_ext}"'
    bat_dir = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}'
    bat_path = f'{bat_dir}/conv_a.bat'
    with open(bat_path, 'w') as f:
        f.write(command)
    p = subprocess.Popen(bat_path, shell=True, stdout=subprocess.PIPE, cwd=bat_dir)
    stdout, stderr = p.communicate()
    result = p.returncode
    os.remove(bat_path)

    if result != 0:
        os.remove(base_audio_path)
        return False

    return audio(movie_id, series_id, audio_lang, audio_ext, base_audio_path, audio_bitrate)


def subs(movie_id, series_id, lang, length):
    series_json = json.loads(get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()['movie']['series'])
    season, series_data = find_series_by_id(series_id, series_json['seasons'])
    is_first_subs = len(series_data['subs']) == 1

    m3u8_data = f"#EXTM3U\n#EXT-X-TARGETDURATION:{length}\n#EXT-X-VERSION:3\n#EXT-X-MEDIA-SEQUENCE:1\n" \
                f"#EXT-X-PLAYLIST-TYPE:VOD\n#EXTINF:{length}.0,\nsubs/{lang}.vtt\n#EXT-X-ENDLIST"

    with open(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/s_{lang}.m3u8', 'w') as f:
        f.write(m3u8_data)

    master_path = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/master.m3u8'
    if is_first_subs:
        add_param_to_streams(master_path, f',SUBTITLES="subs"')
    param = f'#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="{get_lang_full_name(lang)}",' \
            f'DEFAULT={"YES" if lang == "ru" else "NO"},AUTOSELECT=YES,FORCED=NO,LANGUAGE="{lang}",' \
            f'URI="s_{lang}.m3u8"\n\n'
    add_media_param(master_path, param)

    for i in range(len(series_data['subs'])):
        if series_data['subs'][i]['lang'] == lang:
            series_data['subs'][i]['state'] = 1
            break
    series_json = change_series_json(season, series_id, series_data, series_json)
    put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json={'series': json.dumps(series_json)})
