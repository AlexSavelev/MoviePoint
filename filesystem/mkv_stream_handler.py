import os
import subprocess
import shutil
from pathlib import Path
from requests import get, put
import json
from filesystem.ffprobe import FFProbe, FFProbeError
import pysubs2
import webvtt

from filesystem import stream_handler

from misc import *


def put_start_json(movie_id, series_id, tracks):
    series_json = json.loads(get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()['movie']['series'])
    season, series_data = find_series_by_id(series_id, series_json['seasons'])
    for t in tracks['audio']:
        series_data['audio'].append({'lang': t['lang'], 'state': -1})
    for t in tracks['subs']:
        series_data['subs'].append({'lang': t['lang'], 'state': -1})
    series_json = change_series_json(season, series_id, series_data, series_json)
    put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json={'series': json.dumps(series_json)})


def put_bad_json(movie_id, series_id, tracks):
    series_json = json.loads(get(f'{SITE_PATH}/api/v1/movies/{movie_id}').json()['movie']['series'])
    season, series_data = find_series_by_id(series_id, series_json['seasons'])

    series_data['video'] = 0

    audio_lang = [i['lang'] for i in tracks['audio']]
    series_data['audio'] = [i for i in series_data['audio'] if i['lang'] not in audio_lang]

    subs_lang = [i['lang'] for i in tracks['subs']]
    series_data['subs'] = [i for i in series_data['subs'] if i['lang'] not in subs_lang]

    series_json = change_series_json(season, series_id, series_data, series_json)
    put(f'{SITE_PATH}/api/v1/movies/{movie_id}', json={'series': json.dumps(series_json)})


def remove_all_files(series_dir):
    for filename in os.listdir(series_dir):
        file_path = os.path.join(series_dir, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print('Failed to delete %s. Reason: %s' % (file_path, e))
    os.mkdir(f'{series_dir}/subs')  # subs stay


def mkv_extract(series_dir, tracks):
    tracks_cp = " ".join(
        [f'{track["id"]}:{track["fname"]}' for track in (tracks["video"] + tracks["audio"] + tracks["subs"])]
    )
    command = f'"../../mkvextract" src.mkv tracks {tracks_cp}'
    bat_path = f'{series_dir}/mkv_extract.bat'
    with open(bat_path, 'w') as f:
        f.write(command)
    p = subprocess.Popen(bat_path, shell=True, stdout=subprocess.PIPE, cwd=series_dir)
    stdout, stderr = p.communicate()
    result = p.returncode
    os.remove(bat_path)
    return result


def mkv_video_normalize(series_dir, tracks):
    ext = tracks['video'][0]['ext']
    fname = tracks['video'][0]['fname']
    video_path = f'{series_dir}/{fname}'
    try:
        metadata = FFProbe(video_path)
        framerate = int(metadata.video[0].framerate)
        if framerate < 1:
            raise ValueError
    except (IOError, FFProbeError, ValueError):
        return 1

    ext = 'mp4'
    tracks['video'][0]['ext'] = 'mp4'

    command = f'"../../ffmpeg" -y -r {framerate} -i {fname} -c copy src.{ext}'
    bat_path = f'{series_dir}/video_normalize.bat'
    with open(bat_path, 'w') as f:
        f.write(command)
    p = subprocess.Popen(bat_path, shell=True, stdout=subprocess.PIPE, cwd=series_dir)
    stdout, stderr = p.communicate()
    result = p.returncode
    os.remove(bat_path)
    os.remove(video_path)

    tracks['video'][0]['fname'] = f'src.{ext}'  # Working with new video src

    return result


def mkv_video_info(video_path, tracks):
    try:
        metadata = FFProbe(video_path)
        max_height = int(metadata.video[0].height)
        max_bitrate = metadata.video[0].bit_rate
        # max_bitrate = int(metadata.video[0].bit_rate) // 1000
        if not max_bitrate.isdigit() or int(max_bitrate) == 0:
            max_bitrate = (Path(video_path).stat().st_size * 8 // tracks['video'][0]['duration']) // 1000
        else:
            max_bitrate = int(max_bitrate) // 1000
        if max_height < 300 or max_bitrate < 10:
            raise ValueError
    except (IOError, FFProbeError, ValueError):
        return None, None

    streams = build_streams_list(max_height)
    lower_2p_k = [(max_height / i) ** 2 for i in map(lambda x: x[1], streams)]
    bitrates = [int(max_bitrate / k) for k in lower_2p_k]

    return streams, bitrates


def mkv_audio_info(audio_path):
    try:
        metadata = FFProbe(audio_path)
    except (IOError, FFProbeError, ValueError):
        return 0

    try:
        bitrate = int(metadata.audio[0].bit_rate) // 1000
        if bitrate >= 10:
            return bitrate
    except (IOError, FFProbeError, ValueError):
        print('[MKV] audio bitrate not in audio stream, checking metadata')

    try:
        bitrate = int(metadata.metadata['bitrate'].split()[0])
    except (IOError, FFProbeError, ValueError):
        return 0

    return bitrate if bitrate >= 10 else 0


def mkv(movie_id, series_id, tracks):
    put_start_json(movie_id, series_id, tracks)
    series_dir = f'{MEDIA_DATA_PATH}/{movie_id}/{series_id}'
    # Make filenames
    tracks['video'][0]['fname'] = f'mkv_src.{tracks["video"][0]["ext"]}'
    for t in tracks['audio']:
        t['fname'] = f'{t["lang"]}.{t["ext"]}'
    for t in tracks['subs']:
        t['fname'] = f'{t["lang"]}.{t["ext"]}'

    # Extract
    print(f'[MKV] State 0 - EXTRACT')
    result = mkv_extract(series_dir, tracks)

    if result != 0:
        print('[MKV] Fail on state 0')
        remove_all_files(series_dir)
        put_bad_json(movie_id, series_id, tracks)
        return False

    print(f'[MKV] State 1 - VIDEO NORMALIZE')
    result = mkv_video_normalize(series_dir, tracks)

    if result != 0:
        print('[MKV] Fail on state 1')
        remove_all_files(series_dir)
        put_bad_json(movie_id, series_id, tracks)

    print(f'[MKV] State 2 - VIDEO INFO')
    video_path = f"{series_dir}/{tracks['video'][0]['fname']}"
    streams, bitrates = mkv_video_info(video_path, tracks)
    if not streams or not bitrates:
        print('[MKV] Fail on state 2')
        remove_all_files(series_dir)
        put_bad_json(movie_id, series_id, tracks)
        return False

    for stream in streams:
        os.mkdir(f'{series_dir}/stream_{stream[0]}')

    print(f'[MKV] State 3 - AUDIO INFO')
    for t in tracks['audio']:
        t['bitrate'] = mkv_audio_info(f'{series_dir}/{t["fname"]}')
        if t['bitrate'] < 10:
            print(f'[MKV] Fail on state 3 ({t})')
            remove_all_files(series_dir)
            put_bad_json(movie_id, series_id, tracks)
            return False

    for t in tracks['audio']:
        os.mkdir(f'{series_dir}/audio_{t["lang"]}')

    print(f'[MKV] State 4 - SUBS INFO')
    for t in tracks['subs']:
        s_fname = t['fname']
        s_current_path = f'{series_dir}/{s_fname}'
        s_right_path = f'{series_dir}/subs/{t["lang"]}.vtt'
        if t['ext'] == 'vtt':
            os.rename(s_current_path, s_right_path)
        else:
            temp_subs = pysubs2.load(s_current_path, encoding='utf-8')
            temp_subs.save(s_right_path)
            os.remove(s_current_path)
        t['length'] = webvtt.read(s_right_path).total_length

    print(f'[MKV] State 5 - VIDEO')
    t = tracks['video'][0]
    vr = stream_handler.video(movie_id, series_id, t['ext'], f'{series_dir}/{t["fname"]}', streams, bitrates)
    print(f'[MKV] State 5 - VIDEO - 0: code {int(vr)}')
    if not vr:
        print(f'[MKV] Fail on state 5')
        return False

    print(f'[MKV] State 6 - AUDIO')
    for t in tracks['audio']:
        ar = stream_handler.audio(movie_id, series_id, t['lang'], t['ext'], f'{series_dir}/{t["fname"]}', t['bitrate'])
        print(f'[MKV] State 6 - AUDIO - {t["lang"]}: code {int(ar)}')

    print(f'[MKV] State 7 - SUBS')
    for t in tracks['subs']:
        stream_handler.subs(movie_id, series_id, t['lang'], t['length'])
        print(f'[MKV] State 7 - SUBS - {t["lang"]}')

    os.remove(f'{series_dir}/src.mkv')
    print('[MKV] Success')
    return True
