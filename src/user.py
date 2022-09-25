from src.playlist import Playlist

class User:
    def __init__(self, id: str, display_name: str, auth_token: str=None):
        self.id = id
        self.display_name = display_name
        self.playlists = []
        self.playlist_id_map = {}
        self.auth_token = auth_token

    def add_playlist(self, playlist: Playlist):
        if playlist.id in self.playlist_id_map:
            old_playlist = self.playlist_id_map[playlist.id]
            i = self.playlists.index(old_playlist)
            self.playlists[i] = playlist
        else:
            self.playlists.append(playlist)
        self.playlist_id_map[playlist.id] = playlist
