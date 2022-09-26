import os

from src.conf import downloaded_audio_folder as download_folder
from src.ytdownload import get_file_extension_if_exists
from src.persistance.storage import Storage
from src.ytdownload import get_filename_ext


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


class SusTrack:
    def __init__(self, isrc):
        self.isrc = isrc
        self.track = Storage.sus_tracks[self.isrc]
        self.sus_code = self.track['code']
        self.title = self.track['title']
        self.artists = self.track['artists']
        self.url = Storage.isrc_to_access_url[self.isrc]

    def __str__(self):
        artists_str = ', '.join(self.artists)
        sus_str = f'Sus-code: {self.sus_code:<22}'
        track_str = f'Track {artists_str} - {self.title}'
        return f'{sus_str}, {track_str}, isrc: {self.isrc}, current url: {self.url}'


class Track:
    def __init__(self, track_json):
        track = track_json['track']
        self.name = track['name']
        self.spotify_id = track['id'] if 'id' in track else self.name
        self.download_url = ""
        self.artists = [y['name'] for y in track['artists']]
        # TODO: make some logic referring to the db, names might differ
        # TODO: upon decentralized databases which file is with the album name?
        self.filename = self._get_nice_path()
        self.extension = None
        self.duration_ms = track['duration_ms']
        self.duration = self.duration_ms / 1000

        self.added_at = track_json['added_at']
        album = track['album']
        self.album_name = album['name']
        self.album_artists = [x['name'] for x in album['artists']]
        self.track_number = track['track_number']
        self.disc_number = track['disc_number']
        self.release = album['release_date']
        self.arts = album['images']
        self.date_added = self.added_at[:self.added_at.index('T')]
        self.time_added = self.added_at[self.added_at.index('T') + 1:-1]

        # TODO: better handling for no data
        self.is_local = track['is_local']
        if not self.is_local:
            self.isrc = track['external_ids']['isrc']
            self.album_total_tracks = album['total_tracks']


    def add_album_name_to_filename(self):
        self.filename = "%s {%s}" % (self._get_nice_path(), path_encode(self.album_name))


    def add_album_and_isrc_to_filename(self):
        # TODO: nicer path_encode or better isrc validation
        self.filename = "%s {%s} {%s}" % self._get_nice_path(), path_encode(self.album_name), self.isrc


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


    def get_persisted_filename(self):
        # TODO: remove when track objects are created from storage
        return Storage.isrc_to_track_data[self.isrc]['filename'] if self.isrc in Storage.isrc_to_track_data else None


    def __eq__(self, other):
        return isinstance(other, Track) and self.spotify_id == other.spotify_id


    def __hash__(self):
        return hash(self.spotify_id)


    def _get_playlist_entry_string(self, number, formatter, playlist_type):
        filename = self.get_persisted_filename()
        if not filename:
            return None

        filename_with_extension = get_filename_ext(filename, download_folder)
        if not filename_with_extension:
            return None
        fullpath = os.path.join(playlist_type.downloaded_path, filename_with_extension)
        return formatter(filename_with_extension, number, fullpath)

