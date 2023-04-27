import os
import subprocess
import shutil
from pathlib import Path
from requests import get, put
import json
import pysubs2
import webvtt
from filesystem.ffprobe import FFProbe, FFProbeError

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

    series_json = json.loads(get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()['movie']['series'])
    season, series_data = find_series_by_id(series_id, series_json['seasons'])

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

    series_json = json.loads(get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()['movie']['series'])
    season, series_data = find_series_by_id(series_id, series_json['seasons'])
    is_first_audio = len(series_data['audio']) == 1 or all([i['state'] != 1 for i in series_data['audio']])

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
    is_first_subs = len(series_data['subs']) == 1 or all([i['state'] != 1 for i in series_data['subs']])

    m3u8_data = f"#EXTM3U\n#EXT-X-TARGETDURATION:{length}\n#EXT-X-VERSION:3\n#EXT-X-MEDIA-SEQUENCE:1\n" \
                f"#EXT-X-PLAYLIST-TYPE:VOD\n#EXTINF:{length}.0,\nsubs/{lang}.vtt\n#EXT-X-ENDLIST"

    with open(f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/s_{lang}.m3u8', 'w') as f:
        f.write(m3u8_data)

    master_path = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}/master.m3u8'
    if is_first_subs:
        add_param_to_streams(master_path, f',SUBTITLES="subs"')
    param = f'#EXT-X-MEDIA:TYPE=SUBTITLES,GROUP-ID="subs",NAME="{get_lang_full_name(lang)}",' \
            f'DEFAULT={"YES" if is_first_subs else "NO"},AUTOSELECT=YES,FORCED=NO,LANGUAGE="{lang}",' \
            f'URI="s_{lang}.m3u8"\n\n'
    add_media_param(master_path, param)

    for i in range(len(series_data['subs'])):
        if series_data['subs'][i]['lang'] == lang:
            series_data['subs'][i]['state'] = 1
            break
    series_json = change_series_json(season, series_id, series_data, series_json)
    put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json={'series': json.dumps(series_json)})


def mkv(movie_id, series_id, base_mkv_path, tracks):
    tracks['video'][0]['fname'] = f'src.{tracks["video"][0]["ext"]}'
    for t in tracks['audio']:
        t['fname'] = f'{t["lang"]}.{t["ext"]}'
    for t in tracks['subs']:
        t['fname'] = f'{t["lang"]}.{t["ext"]}'

    tracks_cp = " ".join(
        [f'{track["id"]}:{track["fname"]}' for track in (tracks["video"] + tracks["audio"] + tracks["subs"])]
    )

    print(f'[MKV] State 0 - EXTRACT')
    command = f'"../../mkvextract" src.mkv tracks {tracks_cp}'
    bat_dir = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}'
    bat_path = f'{bat_dir}/mkv_extract.bat'
    with open(bat_path, 'w') as f:
        f.write(command)
    p = subprocess.Popen(bat_path, shell=True, stdout=subprocess.PIPE, cwd=bat_dir)
    stdout, stderr = p.communicate()
    result = p.returncode
    os.remove(bat_path)

    series_json = json.loads(get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()['movie']['series'])
    season, series_data = find_series_by_id(series_id, series_json['seasons'])

    if result != 0:
        print('[MKV] Fail on state 0')
        os.remove(base_mkv_path)
        series_data['video'] = 0
        series_json = change_series_json(season, series_id, series_data, series_json)
        put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json={'series': json.dumps(series_json)})
        return False

    base_dir = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}'

    print(f'[MKV] State 1 - VIDEO INFO')
    base_video_path = f'{base_dir}/{tracks["video"][0]["fname"]}'
    try:
        metadata = FFProbe(base_video_path)
        max_height = int(metadata.video[0].height)
        max_bitrate = metadata.video[0].bit_rate
        # max_bitrate = int(metadata.video[0].bit_rate) // 1000
        if not max_bitrate.isdigit() or int(max_bitrate) == 0:
            max_bitrate = (Path(base_video_path).stat().st_size * 8 // tracks["video"][0]['duration']) // 1000
        else:
            max_bitrate = int(max_bitrate) // 1000
        if max_height < 300 or max_bitrate < 10:
            raise ValueError
    except (IOError, FFProbeError, ValueError):
        print('[MKV] Fail on state 1')
        os.remove(base_video_path)
        series_data['video'] = 0
        series_json = change_series_json(season, series_id, series_data, series_json)
        put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json={'series': json.dumps(series_json)})
        return False

    streams = build_streams_list(max_height)
    lower_2p_k = [(max_height / i) ** 2 for i in map(lambda x: x[1], streams)]
    bitrates = [int(max_bitrate / k) for k in lower_2p_k]
    for stream in streams:
        os.mkdir(f'{base_dir}/stream_{stream[0]}')

    print(f'[MKV] State 2 - AUDIO INFO')
    for t in tracks['audio']:
        os.mkdir(f'{base_dir}/audio_{t["lang"]}')

    print(f'[MKV] State 3 - SUBS INFO')
    for t in tracks['subs']:
        ext = t['ext']
        fname = t['fname']
        f_path = f'{base_dir}/{fname}'
        r_path = f'{base_dir}/subs/{fname}'
        if ext == 'vtt':
            os.rename(f_path, r_path)
        else:
            temp_subs = pysubs2.load(f_path, encoding='utf-8')
            temp_subs.save(r_path)
            os.remove(f_path)
        t['length'] = webvtt.read(r_path).total_length

    print(f'[MKV] State 4 - ADD SERIES INFO')
    series_json = json.loads(get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()['movie']['series'])
    season, series_data = find_series_by_id(series_id, series_json['seasons'])
    for t in tracks['audio']:
        series_data['audio'].append({'lang': t['lang'], 'state': -1})
    for t in tracks['subs']:
        series_data['subs'].append({'lang': t['lang'], 'state': -1})
    series_json = change_series_json(season, series_id, series_data, series_json)
    put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json={'series': json.dumps(series_json)})

    print(f'[MKV] State 5 - VIDEO')
    t = tracks['video'][0]
    vr = video(movie_id, series_id, t['ext'], base_video_path, streams, bitrates)
    if not vr:
        print(f'[MKV] Fail on state 4')
        return False

    print(f'[MKV] State 6 - AUDIO')
    for t in tracks['audio']:
        ar = audio(movie_id, series_id, t['lang'], t['ext'], f'{base_dir}/{t["fname"]}', t['bitrate'])
        print(f'[MKV] State 6 - AUDIO - {t["lang"]}: code {int(ar)}')

    print(f'[MKV] State 7 - SUBS')
    for t in tracks['subs']:
        subs(movie_id, series_id, t['lang'], t['length'])
        print(f'[MKV] State 7 - SUBS - {t["lang"]}')

    print('[MKV] Success')
    return True
