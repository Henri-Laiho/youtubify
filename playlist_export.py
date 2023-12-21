import argparse
import json
import os

from src.composition import add_compositions
from src.track import fullwidth_path_encoding
from src.track import path_encode
from src.file_index import FileIndex
from src.playlist_format import PlaylistFormat
from src.youtube.playlists import get_authenticated_service, update_playlist, get_youtube_playlists, \
    is_daily_youtube_quota_reached

try:
    from conf.conf_playlist_export import playlist_types
except ImportError:
    playlist_types = None
    print('Copy ./conf/conf_playlist_export.py.example to ./conf/conf_playlist_export.py and modify if needed.')
    exit(-1)
from src import conf
from src.persistance.storage import Storage
from src.ytdownload import ensure_dir

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


def prepare_dirs():
    ensure_dir(conf.playlists_export_folder)

    for playlist_type in playlist_types:
        directory = os.path.join(conf.playlists_export_folder, playlist_type.playlist_file_prefix)
        ensure_dir(directory)

        # Delete all playlist files in the playlist directory
        for filename in os.listdir(directory):
            if filename.endswith(extension):
                os.remove(os.path.join(directory, filename))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--no_local', action='store_true', help='don\'t include local files', default=False)
    parser.add_argument('-y', '--youtube', action='store_true', help='export to youtube instead', default=False)
    args = parser.parse_args()
    Storage.storage_setup()
    no_local = args.no_local
    to_youtube = args.youtube
    youtube = None
    yt_playlists = None
    if to_youtube:
        youtube = get_authenticated_service()
        if is_daily_youtube_quota_reached():
            exit(-1)
        yt_playlists = get_youtube_playlists(youtube)

    local_file_index = FileIndex(conf.spotify_local_files_folders)
    flac_file_index = FileIndex([conf.flacified_audio_folder])

    prepare_dirs()

    with open(conf.playlists_file, "r") as f:
        playlists_json = json.loads(f.read())
    if not playlists_json:
        exit(-1)

    playlists = add_compositions(playlists_json)

    for i, playlist in enumerate(playlists):
        list_name = playlist.get_displayname()
        print(i, list_name)

        if to_youtube:
            video_links = [x for x in [Storage.get_access_url(x.isrc) for x in playlist.tracks if x.isrc is not None] if
                           x is not None]
            update_playlist(youtube, "(S) " + list_name, video_links, yt_playlists)
        else:
            for playlist_type in playlist_types:
                directory = os.path.join(conf.playlists_export_folder, playlist_type.playlist_file_prefix)

                lines = playlist.to_format(playlist_format, playlist_type,
                                           flac_file_index if playlist_type.flac else local_file_index, no_local)

                with open(
                        os.path.join(directory, path_encode(list_name, fullwidth_path_encoding) + extension),
                        mode='w+',
                        encoding='utf8') as f:
                    for line in lines:
                        f.write(line + '\n')

    Storage.save()
    print('Data saved.')
