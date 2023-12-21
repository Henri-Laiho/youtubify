import os
import posixpath
import ntpath

from src import conf


class PlaylistExportDevice:
    def __init__(self, downloaded_path=os.path.abspath(conf.downloaded_audio_folder),
                 spotify_missing_paths=conf.spotify_local_files_folders,
                 flacified_path=os.path.abspath(conf.flacified_audio_folder),
                 playlist_file_prefix='', os_path=posixpath, flac=False):
        self.downloaded_path = downloaded_path
        self.spotify_missing_paths = spotify_missing_paths
        self.flacified_path = flacified_path
        self.playlist_file_prefix = playlist_file_prefix
        self.os_path = os_path
        self.flac = flac

    def get_file_full_path(self, filename: str):
        return self.os_path.join(self.flacified_path if self.flac else self.downloaded_path, filename)
