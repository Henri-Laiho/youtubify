import os

playlists_export_folder = 'playlists'
playlists_file = 'playlists.json'
spotify_unsupported_preview_suffix_ext = '.lq-preview.mp3'
spotify_unsupported_preview_suffix = '.lq-preview'
downloaded_audio_folder = 'downloaded'
downloaded_artwork_folder = os.path.join(downloaded_audio_folder, 'art')


class Flags:
    development = False
    profile = 'ytfy'
    max_download_errors = 1000
