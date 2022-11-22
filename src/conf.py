import os

playlists_file = 'playlists.json'
spotify_unsupported_preview_suffix_ext = '.lq-preview.m4a'
spotify_unsupported_preview_suffix = '.lq-preview'
try:
    from conf.conf_private import playlists_export_folder
except ImportError:
    playlists_export_folder = 'playlists'
try:
    from conf.conf_private import data_folder
except ImportError:
    data_folder = 'data'
try:
    from conf.conf_private import data_export_folders
    if isinstance(data_export_folders, str):
        data_export_folders = [data_export_folders]
    if not isinstance(data_export_folders, list):
        raise RuntimeError('invalid data_export_folders configuration in ./conf/conf_private.py')
except ImportError:
    data_export_folders = [os.path.join(data_folder, 'sync')]
try:
    from conf.conf_private import spotify_local_files_folders
except ImportError:
    spotify_local_files_folders = None
try:
    from conf.conf_private import downloaded_audio_folder
except ImportError:
    downloaded_audio_folder = 'downloaded'
downloaded_artwork_folder = os.path.join(downloaded_audio_folder, 'art')



class Flags:
    max_download_errors = 1000
