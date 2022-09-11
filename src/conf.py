import os

playlists_file = 'playlists.json'
spotify_unsupported_preview_suffix_ext = '.lq-preview.m4a'
spotify_unsupported_preview_suffix = '.lq-preview'
try:
    from src.conf_private import playlists_export_folder
except ImportError:
    playlists_export_folder = 'playlists'
try:
    from src.conf_private import downloaded_audio_folder
except ImportError:
    downloaded_audio_folder = 'downloaded'
downloaded_artwork_folder = os.path.join(downloaded_audio_folder, 'art')


class Flags:
    profile = 'ytfy'
    max_download_errors = 1000
