import argparse
import json
import os

from src.conf import spotify_unsupported_preview_suffix
from src.downloader import get_nice_path

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


def format_track(list_track, number, formatter, playlist_type):
    track = list_track['track']
    isrc = track['external_ids']['isrc']
    if isrc not in Storage.isrc_to_track_data:
        return None
    data = Storage.isrc_to_track_data[isrc]
    title = data['title']
    artists = data['artists']

    fname = get_filename_ext(data['filename'], conf.downloaded_audio_folder)
    if fname is None:
        return None
    fullpath = os.path.join(playlist_type.downloaded_path, fname)
    return formatter(fname, number, fullpath)


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
    for i, playlist in enumerate(data):
        list_name = playlist['name']
        print(i, list_name)

        for playlist_type in playlist_types:
            directory = os.path.join(conf.playlists_export_folder, playlist_type.playlist_file_prefix)
            ensure_dir(directory)
            f = open(
                os.path.join(directory, playlist_type.playlist_file_prefix + '_' + list_name + extension),
                mode='w+',
                encoding='utf8')

            if header is not None:
                f.write(header + '\n')
            for j, x in enumerate(playlist['tracks']):
                if x['track']['is_local']:
                    if no_local:
                        continue

                    fname = get_nice_path(x['track']['name'], [artist['name'] for artist in x['track']['artists']])
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
                    entry = format_track(x, j, formatter, playlist_type)
                if entry is not None:
                    f.write(entry + '\n')

            f.close()
