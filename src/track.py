import os

from src.conf import downloaded_audio_folder as download_folder
from src.ytdownload import get_file_extension_if_exists


nice_path_encoding = {
    '\\': '',
    '/': '',
    ':': '',
    '*': '',
    '?': '',
    '"': '\'',
    '<': '',
    '>': '',
    '|': '',
    '%': '',
}


def path_encode(path, encoding=nice_path_encoding):
        for key in encoding:
            path = path.replace(key, encoding[key])
        return path

class Track:
    def __init__(self, track_json):
        track = track_json['track']
        self.is_local = track['is_local']
        if not self.is_local:
            self.isrc = track['external_ids']['isrc']
        self.name = track['name']
        self.download_url = ""
        self.artists = [y['name'] for y in track['artists']]
        # TODO: make some logic referring to the db, names might differ
        # TODO: upon decentralized databases which file is with the album name?
        self.filename = self._get_nice_path()
        self.extension = None
        self.duration_ms = track['duration_ms']
        self.duration = self.duration_ms / 1000

        self.added_at = track_json['added_at']
        self.album_name = track['album']['name']
        self.release = track['album']['release_date']
        self.arts = track['album']['images']
        self.date_added = self.added_at[:self.added_at.index('T')]
        self.time_added = self.added_at[self.added_at.index('T') + 1:-1]

    def add_album_name_to_filename(self):
        self.filename ="%s {%s}" % (self._get_nice_path(), path_encode(self.album_name))

    def add_album_and_isrc_to_filename(self):
        # TODO: nicer path_encode or better isrc validation
        self.filename ="%s {%s} {%s}" % self._get_nice_path(), path_encode(self.album_name), self.isrc


    def _get_nice_path(self):
        if len(self.artists) > 0 and self.artists[0]:
            return path_encode(self.artists[0] + ' - ' + self.name, nice_path_encoding)
        else:
            return path_encode(self.name, nice_path_encoding)

    def update_file_extension(self, old_name):
        self.extension = get_file_extension_if_exists(old_name, download_folder)

    def update_filename_on_disk(self, old_filename):
        if not self.extension: self.update_file_extension(old_filename)
        if not self.extension: return

        old_path = os.path.join(download_folder, old_filename + self.extension)
        new_path = os.path.join(download_folder, self.filename + self.extension)

        print('Names changed: renaming file "%s" to "%s"' % (old_filename, self.filename))
        os.rename(old_path, new_path)

    def set_download_url(self, url):
        self.download_url = url
