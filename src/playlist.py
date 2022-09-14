from src.track import Track
from src.playlist_format import PlaylistFormat


class Playlist:
	def __init__(self):
		self.tracks = []
		self.id = None
		self.name = None


	def to_format(self, format: PlaylistFormat):
		raise NotImplementedError
		result = []
		if format.header:
			result.append(format.header)

		for i, track in enumerate(self.tracks):
			pass
		return result


	@staticmethod
	def from_json(playlist_json):
		playlist = Playlist()
		playlist.tracks = [Track(x) for x in playlist_json['tracks']]
		playlist.id = playlist_json['id']
		playlist.name = playlist_json['name']
		return playlist

