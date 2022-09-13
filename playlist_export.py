import argparse
import json
import os

from src.conf import spotify_unsupported_preview_suffix
from src.track import Track

try:
    from conf_playlist_export import playlist_types
except ImportError:
    playlist_types = None
    print('Copy conf_playlist_export.py.example to conf_playlist_export.py and modify if needed.')
    exit(-1)
from src import conf, downloader
from src.persistance.track_data import add_storage_argparse, storage_setup, Storage
from src.ytdownload import ensure_dir, get_filename_ext

try:
    from src.conf_private import spotify_local_files_folders
except ImportError:
    spotify_local_files_folders = None

mode = 'm3u8'


def format_m3u8(fname: str, number: int, fullpath: str):
    return "#EXTINF:%d,%s%s%s" % (number, fname, '\n', fullpath)


def format_simple(fname: str, number: int, fullpath: str):
    return fname


if mode == 'm3u8':
    header = "#EXTM3U"
    formatter = format_m3u8
    extension = '.m3u8'
elif mode == 'simple':
    header = None
    formatter = format_simple
    extension = '.txt'
else:
    raise RuntimeError('Invalid mode')


def format_track(track : Track, number, formatter, playlist_type):
    filename = track.get_persisted_filename()
    if not filename:
        return None

    fname = get_filename_ext(filename, conf.downloaded_audio_folder)
    if fname is None:
        return None
    fullpath = os.path.join(playlist_type.downloaded_path, fname)
    return formatter(fname, number, fullpath)


def join_playlists(p1, p2):
    tracks = p1['tracks'][:]
    ids = {x['track']['id'] if x['track']['id'] is not None else x['track']['name'] for x in tracks}
    for y in p2['tracks']:
        id = y['track']['id'] if y['track']['id'] is not None else y['track']['name']
        if id not in ids:
            tracks.append(y)
            ids.add(id)
    return {
        'name': '%s & %s' % (p1['name'], p2['name']), 
        'tracks': tracks
        }


def add_compositions(playlists):
    id_to_plist = {x['id'] if 'id' in x else '0' : x for x in playlists}
    for name in Storage.playlist_compositions:
        prev = None
        for id in Storage.playlist_compositions[name]:
            playlist = id_to_plist[id]
            if prev is not None:
                prev = join_playlists(prev, playlist)
            else:
                prev = playlist
        prev['name'] = "%s (%s)" % (name, prev['name'])
        playlists.append(prev)
    return playlists


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    add_storage_argparse(parser)
    parser.add_argument('--no_local', action='store_true', help='don\'t include local files', default=False)
    args = parser.parse_args()
    storage_setup(args)
    no_local = args.no_local

    f = open(conf.playlists_file, "r")
    data = json.loads(f.read())
    f.close()

    local_file_map = {}
    local_folder_map = {}
    if spotify_local_files_folders:
        for spotify_local_files_folder in spotify_local_files_folders:
            for i in os.listdir(spotify_local_files_folder):
                key = i[:i.rindex('.')]
                if key in local_file_map:
                    print('WARNING: track', key, 'has multiple instances in spotify local files')
                local_file_map[key] = i
                local_folder_map[key] = spotify_local_files_folder
    spotify_local_files_folders_index = {x: i for i, x in enumerate(spotify_local_files_folders)}

    ensure_dir(conf.playlists_export_folder)
    data = add_compositions(data)
    for i, playlist in enumerate(data):
        list_name = playlist['name']
        print(i, list_name)
        tracks = list(map(Track, playlist['tracks']))

        for playlist_type in playlist_types:
            directory = os.path.join(conf.playlists_export_folder, playlist_type.playlist_file_prefix)
            ensure_dir(directory)
            f = open(
                os.path.join(directory, playlist_type.playlist_file_prefix + '_' + list_name + extension),
                mode='w+',
                encoding='utf8')

            if header is not None:
                f.write(header + '\n')
            for j, track in enumerate(tracks):
                if track.is_local:
                    if no_local:
                        continue

                    fname = track._get_nice_path()
                    if fname.endswith(spotify_unsupported_preview_suffix):
                        filename = fname[:-len(spotify_unsupported_preview_suffix)]
                        key = filename[:filename.rindex('.')]
                        idx = spotify_local_files_folders_index[local_folder_map[key]]
                    else:
                        if fname not in local_file_map:
                            print('ERROR:', fname, 'not found in local files')
                            continue
                        filename = local_file_map[fname]
                        idx = spotify_local_files_folders_index[local_folder_map[fname]]
                    path = os.path.join(playlist_type.spotify_missing_paths[idx], filename)
                    entry = formatter(filename, j, path)
                else:
                    entry = format_track(track, j, formatter, playlist_type)
                if entry is not None:
                    f.write(entry + '\n')

            f.close()
