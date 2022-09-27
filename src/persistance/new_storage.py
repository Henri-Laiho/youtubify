from src.composition import Composition
from src.playlist import Playlist


class NewStorage():
    _storage = None

    @staticmethod
    def get_storage():
        if not NewStorage._storage:
            NewStorage._storage = NewStorage()
        return NewStorage._storage

    def __init__(self, database):
        self.database = database
        self.playlists = self.get_playlists()
        self.compilations = self.get_compilations()
        self.spotify_token = self.get_spotify_token()

    def reset(self):
        pass

    def load_dict(self, data):
        pass

    def get_save_dict(self):
        pass

    def set_track_data(self, isrc: str, artists: list, title: str, filename: str):
        pass

    def add_sus_track(self, isrc: str, search_results=None, artists: list = None, title: str = None, code='', data=None):
        pass

    def set_sus_track(self, isrc: str, search_results=None, artists: list = None, title: str = None, code='', data=None):
        pass

    def ignore_track(self, isrc: str):
        pass

    def reset_track(self, isrc: str, force=False):
        pass

    def confirm(self, isrc):
        pass

    def add_access_url(self, isrc: str, url: str):
        pass

    def set_active_playlist(playlist_id: str, active: bool):
        pass

    def is_active_playlist(playlist_id: str):
        pass

    def get_access_url(isrc: str):
        pass

    def set_autogen_track(isrc: str):
        pass

    def get_private_isrc(title: str, artists, duration_floor_s: int):
        pass

    def load(filename=None):
        pass

    def save(file=None):
        pass

    def get_playlist(self, playlist_id):
        return self.database.get_playlist(playlist_id)

    def get_playlists(self):
        return self.database.get_playlists()

    def get_compilations(self):
        return self.database.get_compilations()

    def get_compilation(self, compilation_id):
        return self.database.get_compilation(compilation_id)

    def get_spotify_token(self):
        return self.database.get_spotify_token()

    def add_playlist(self, playlist: Playlist):
        return self.database.add_playlist(playlist)

    def add_compilation(self, compilation: Composition):
        return self.database.add_compilation(compilation)

    def sync_with_spotify(self):
        pass