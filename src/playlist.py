import os

from src.persistance.track_data import Storage
from src.track import Track
from src.playlist_format import PlaylistFormat
from src.file_index import FileIndex
from src.conf import spotify_unsupported_preview_suffix


class Playlist:
    def __init__(self):
        self.tracks = []
        self.id = None
        self.name = None
        self.is_active = False
        isrc_map = {}
        
        
    def to_format(self, format: PlaylistFormat, playlist_type, local_files_index : FileIndex, skip_local_files: bool):
        lines = []
        
        if format.header is not None:
            lines.append(format.header)
        for j, track in enumerate(self.tracks):
            entry = None
            if track.is_local:
                if skip_local_files:
                    continue

                fname = track.filename
                if fname.endswith(spotify_unsupported_preview_suffix):
                    filename = fname[:-len(spotify_unsupported_preview_suffix)]
                    filename_no_suffix = filename[:filename.rindex('.')]
                    idx = local_files_index.which_folder(filename_no_suffix)
                elif fname in local_files_index.file_map:
                    filename = local_files_index.file_map[fname]
                    idx = local_files_index.which_folder(fname)
                else:
                    print('ERROR:', fname, 'not found in local files')
                    continue
                path = os.path.join(playlist_type.spotify_missing_paths[idx], filename)
                entry = format.formatter(filename, j, path)
            else:
                entry = track._get_playlist_entry_string(j, format.formatter, playlist_type)
            if entry:
                lines.append(entry)
        return lines
    
    
    @staticmethod
    def from_json(playlist_json):
        playlist = Playlist()
        playlist.tracks = [Track(x) for x in playlist_json['tracks']]
        # TODO: liked songs id = user id
        playlist.id = playlist_json['id'] if 'id' in playlist_json else '0'
        playlist.name = playlist_json['name']
        # TODO: remove or consolidate accessing Storage outside this class
        playlist.is_active = Storage.is_active_playlist(playlist.id)
        playlist.isrc_map = {x.isrc : x for x in playlist.tracks if not x.is_local}
        return playlist


    def toggle_is_active(self):
        self.is_active = not Storage.is_active_playlist(self.id)
        Storage.set_active_playlist(self.id, self.is_active)
        

    def is_in_composition(self, composition: dict):
        return self.id in composition

    
    def get_menu_string_with_active_state(self):
        return f"{'+' if self.is_active else ' '} {self.name}"


    def __str__(self):
        return self.name
    
    