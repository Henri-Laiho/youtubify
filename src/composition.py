from src.playlist import Playlist


def order_by_date_added(tracks: list):
	return sorted(tracks, key=lambda x: '' if x.is_local else x.date_added + x.time_added)


class Composition:
	def __init__(self, name, with_duplicates: bool=False, order_by_date_added: bool=True):
		self.playlists = []
		self.playlist_ids = set()
		self.name = name
		self.with_duplicates = with_duplicates
		self.order_by_date_added = order_by_date_added

	def add_playlist(self, playlist: Playlist):
		self.playlists.append(playlist)

	def to_playlist(self):
		tracks = self._get_tracks_with_duplicates()
		ordered_tracks = order_by_date_added(tracks) if self.order_by_date_added else tracks

		result = Playlist()
		result.tracks = ordered_tracks if self.with_duplicates else list(dict.fromkeys(ordered_tracks))
		result.tracks.reverse()

		playlist_names = ' & '.join([x.name for x in self.playlists])
		result.name = f"{self.name} ({playlist_names})"
		return result

	def _get_tracks_with_duplicates(self):
		tracks = []
		for playlist in self.playlists:
			tracks += playlist.tracks
		return tracks


