from src.playlist import Playlist


class Composition:
	def __init__(self, name):
		self.playlists = []
		self.playlist_ids = set()
		self.name = name


	def add_playlist(self, playlist: Playlist):
		self.playlists.append(playlist)


	def to_playlist(self, with_duplicates: bool=False):
		if with_duplicates:
			tracks = self._get_tracks_with_duplicates()
		else:
			tracks = self._get_tracks_without_duplicates()

		result = Playlist()
		result.tracks = tracks
		playlist_names = ' & '.join([x.name for x in self.playlists])
		result.name = f"{self.name} ({playlist_names})"
		return result


	def _get_tracks_without_duplicates(self):
		tracks = set()
		for playlist in self.playlists:
			tracks.update(playlist.tracks)
		return list(tracks)
		

	def _get_tracks_with_duplicates(self):
		tracks = []
		for playlist in self.playlists:
			tracks += playlist.tracks
		return tracks

