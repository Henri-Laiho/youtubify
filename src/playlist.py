import os

from src.persistance.storage import Storage
from src.track import Track
from src.playlist_format import PlaylistFormat
from src.playlist_export_device import PlaylistExportDevice
from src.file_index import FileIndex
from src.conf import spotify_unsupported_preview_suffix


class Playlist:
    def __init__(self):
        self.snapshot_id = None
        self.tracks = []
        self.id = None
        self.name = None
        self.is_active = False
        self.isrc_map = {}

    def to_format(self, format: PlaylistFormat, playlist_type: PlaylistExportDevice, local_files_index: FileIndex, skip_local_files: bool):
        lines = []
        
        if format.header is not None:
            lines.append(format.header)
        for j, track in enumerate(self.tracks):
            entry = None
            if track.is_local:
                if skip_local_files:
                    continue

                fname = track.filename
                filename_no_extension = fname
                if fname.endswith(spotify_unsupported_preview_suffix):
                    filename_no_suffix = fname[:-len(spotify_unsupported_preview_suffix)]
                    filename_no_extension = filename_no_suffix[:filename_no_suffix.rindex('.')]

                if filename_no_extension in local_files_index.file_map:
                    filename = local_files_index.file_map[filename_no_extension]
                    index = local_files_index.which_folder(filename_no_extension)
                else:
                    print('ERROR:', filename_no_extension, 'not found in local files')
                    continue
                if index >= len(playlist_type.spotify_missing_paths):
                    print('WARNING: device', playlist_type.playlist_file_prefix, 'configuration does not have enough local files folders')
                    continue
                path = playlist_type.os_path.join(playlist_type.spotify_missing_paths[index], filename)
                entry = format.formatter(filename, j, path)
            else:
                entry = track._get_playlist_entry_string(j, format.formatter, playlist_type)
            if entry:
                lines.append(entry)
        return lines

    @staticmethod
    def from_json(playlist_json):
        playlist = Playlist()
        playlist.set_tracks(playlist_json['tracks'])
        playlist.set_metadata(playlist_json)
        # TODO: remove or consolidate accessing Storage outside this class
        playlist.is_active = Storage.is_active_playlist(playlist.id)
        return playlist

    def set_metadata(self, playlist_json):
        self.id = playlist_json['id']
        self.name = playlist_json['name']
        if 'snapshot_id' in playlist_json:
            self.snapshot_id = playlist_json['snapshot_id']

    def set_tracks(self, tracks_json):
        self.tracks = [Track.from_spotify_json(x) for x in tracks_json]
        self.isrc_map = {x.isrc : x for x in self.tracks if not x.is_local}

    def toggle_is_active(self):
        self.set_active(not Storage.is_active_playlist(self.id))

    def set_active(self, is_active):
        self.is_active = is_active
        Storage.set_active_playlist(self.id, self.is_active)

    def is_in_composition(self, composition: dict):
        return self.id in composition

    def get_menu_string_with_active_state(self):
        return f"{'+' if self.is_active else ' '} {self.name if self.name else self.id}"

    # TODO: use composition class instead of dict
    def get_menu_string_with_composition_status(self, composition: dict):
        return f"{'+' if self.is_in_composition(composition) else ' '} {self.name if self.name else self.id}"

    def __str__(self):
        return self.name if self.name else self.id
    
    