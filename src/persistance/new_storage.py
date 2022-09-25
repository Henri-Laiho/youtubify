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