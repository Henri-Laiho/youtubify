import argparse
import json
import os

from src.track import fullwidth_path_encoding
from src.track import path_encode
from src.track import Track
from src.playlist import Playlist
from src.file_index import FileIndex
from src.local_files import LocalFileManager
from src.composition import Composition
from src.playlist_format import PlaylistFormat

try:
    from conf.conf_playlist_export import playlist_types
except ImportError:
    playlist_types = None
    print('Copy ./conf/conf_playlist_export.py.example to ./conf/conf_playlist_export.py and modify if needed.')
    exit(-1)
from src import conf, downloader
from src.persistance.storage import Storage
from src.ytdownload import ensure_dir, get_filename_ext

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
    filemgr = LocalFileManager()

    # TODO: parse playlists_json to Playlist objects in another function
    playlists = [Playlist.from_json(x) for x in playlists_json] + filemgr.get_playlists()
    id_to_plist = {x.id : x for x in playlists}

    for composition_name, playlist_ids in Storage.playlist_compositions.items():
        comp = Composition(composition_name)

        for playlist_id in playlist_ids:
            comp.add_playlist(id_to_plist[playlist_id])

        playlists.append(comp.to_playlist())
    return playlists


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--no_local', action='store_true', help='don\'t include local files', default=False)
    args = parser.parse_args()
    Storage.storage_setup()
    no_local = args.no_local

    local_file_index = FileIndex(conf.spotify_local_files_folders)

    ensure_dir(conf.playlists_export_folder)

    with open(conf.playlists_file, "r") as f:
        playlists_json = json.loads(f.read())
    if not playlists_json:
        exit(-1)

    playlists = add_compositions(playlists_json)

    for i, playlist in enumerate(playlists):
        list_name = playlist.name if playlist.name else playlist.id
        print(i, list_name)

        for playlist_type in playlist_types:
            directory = os.path.join(conf.playlists_export_folder, playlist_type.playlist_file_prefix)
            ensure_dir(directory)

            lines = playlist.to_format(playlist_format, playlist_type, local_file_index, no_local)

            with open(
                os.path.join(directory, path_encode(list_name, fullwidth_path_encoding) + extension),
                mode='w+',
                encoding='utf8') as f:
                for line in lines:
                    f.write(line + '\n')
