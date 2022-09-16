from src.track import Track
from src.playlist_format import PlaylistFormat


class Playlist:
	def __init__(self):
		self.tracks = []
		self.id = None
		self.name = None
		isrc_map = {}


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
		# TODO: liked songs id = user id
		playlist.id = playlist_json['id'] if 'id' in playlist_json else '0'
		playlist.name = playlist_json['name']
		playlist.isrc_map = {x.isrc : x for x in playlist.tracks if not x.is_local}
		return playlist

