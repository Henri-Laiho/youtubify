import json

from src.composition import Composition
from src.playlist import Playlist


class JsonFileStorage:

    def __init__(self, filename: str):
        with open(filename, 'r') as database:
            self.data = json.loads(database.read())

    def get_playlist(self, playlist_id):
        pass

    def get_playlists(self):
        pass

    def get_compilations(self):
        pass

    def get_compilation(self, compilation_id):
        pass

    def get_spotify_token(self):
        pass

    def add_playlist(self, playlist: Playlist):
        pass

    def add_compilation(self, compilation: Composition):
        pass