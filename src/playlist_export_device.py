import os
import posixpath
import ntpath

from src import conf


class PlaylistExportDevice:
    def __init__(self, downloaded_path=os.path.abspath(conf.downloaded_audio_folder), spotify_missing_paths=conf.spotify_local_files_folders, playlist_file_prefix='', os_path=posixpath):
        self.downloaded_path = downloaded_path
        self.spotify_missing_paths = spotify_missing_paths
        self.playlist_file_prefix = playlist_file_prefix
        self.os_path = os_path

    def get_dl_full_path(self, filename: str):
        return self.os_path.join(self.downloaded_path, filename)
