import argparse
import json
import os

from src.track import Track
from src.playlist import Playlist
from src.file_index import FileIndex
from src.composition import Composition
from src.playlist_format import PlaylistFormat

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

# TODO: implement UI for mode choice
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

playlist_format = PlaylistFormat('m3u8', "#EXTM3U", format_m3u8, '.m3u8')


def add_compositions(playlists_json):
    # TODO: enter id in spotify_import.py script
    playlists_json[0]['id'] = '0'
    # TODO: parse playlists_json to Playlist objects in another function
    playlists = [Playlist.from_json(x) for x in playlists_json]
    id_to_plist = {x.id : x for x in playlists}

    for composition_name, playlist_ids in Storage.playlist_compositions.items():
        comp = Composition(composition_name)

        for playlist_id in playlist_ids:
            comp.add_playlist(id_to_plist[playlist_id])

        playlists.append(comp.to_playlist())
    return playlists


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    add_storage_argparse(parser)
    parser.add_argument('--no_local', action='store_true', help='don\'t include local files', default=False)
    args = parser.parse_args()
    storage_setup(args)
    no_local = args.no_local

    local_file_index = FileIndex(spotify_local_files_folders)

    ensure_dir(conf.playlists_export_folder)

    with open(conf.playlists_file, "r") as f:
        playlists_json = json.loads(f.read())
    if not playlists_json:
        exit(-1)

    playlists = add_compositions(playlists_json)


    for i, playlist in enumerate(playlists):
        list_name = playlist.name
        print(i, list_name)

        for playlist_type in playlist_types:
            directory = os.path.join(conf.playlists_export_folder, playlist_type.playlist_file_prefix)
            ensure_dir(directory)

            lines = playlist.to_format(playlist_format, playlist_type, local_file_index, no_local)

            with open(
                os.path.join(directory, playlist_type.playlist_file_prefix + '_' + list_name + extension),
                mode='w+',
                encoding='utf8') as f:
                for line in lines:
                    f.write(line + '\n')

