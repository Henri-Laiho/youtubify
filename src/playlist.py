from src.persistance.storage import Storage
from src.track import Track
from src.playlist_format import PlaylistFormat
from src.playlist_export_device import PlaylistExportDevice
from src.file_index import FileIndex


class Playlist:
    def __init__(self):
        self.snapshot_id = None
        self.tracks = []
        self.id = None
        self.name = None
        self.is_active = False
        self.is_flacify = False
        self.isrc_map = {}
        self.creator_dn = None

    def to_format(self, format: PlaylistFormat, playlist_type: PlaylistExportDevice, local_files_index: FileIndex, skip_local_files: bool):
        lines = []
        
        if format.header is not None:
            lines.append(format.header)
        for j, track in enumerate(self.tracks):
            if track.is_local:
                if skip_local_files:
                    continue

                index, filename = track.get_local_folder_idx_and_filename(local_files_index)
                if not filename:
                    continue
                if index >= len(playlist_type.spotify_missing_paths):
                    print('WARNING: device', playlist_type.playlist_file_prefix,
                          'configuration does not have enough local files folders')
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
        playlist.is_flacify = Storage.is_flacify_playlist(playlist.id)
        return playlist

    def set_metadata(self, playlist_json):
        self.id = playlist_json['id']
        self.name = playlist_json['name']
        if 'snapshot_id' in playlist_json:
            self.snapshot_id = playlist_json['snapshot_id']
        if 'owner' in playlist_json and 'display_name' in playlist_json['owner']:
            self.creator_dn = playlist_json['owner']['display_name']
        elif self.name == 'Liked Songs':
            self.creator_dn = self.id

    def set_tracks(self, tracks_json):
        self.tracks = [Track.from_spotify_json(x) for x in tracks_json]
        self.isrc_map = {x.isrc : x for x in self.tracks if not x.is_local}

    def toggle_is_flacify(self):
        self.set_flacify(not Storage.is_flacify_playlist(self.id))

    def set_flacify(self, is_flacify):
        self.is_flacify = is_flacify
        Storage.set_flacify_playlist(self.id, self.is_flacify)

    def toggle_is_active(self):
        self.set_active(not Storage.is_active_playlist(self.id))

    def set_active(self, is_active):
        self.is_active = is_active
        Storage.set_active_playlist(self.id, self.is_active)

    def is_in_composition(self, composition: dict):
        return self.id in composition

    def get_menu_string_with_active_state(self):
        return f"{'+' if self.is_active else ' '} {self.get_displayname()}"

    def get_menu_string_with_flacify_state(self):
        return f"{'+' if self.is_flacify else ' '} {self.get_displayname()}"

    def get_displayname(self, with_creator_dn=True):
        return f"{self.name if self.name else self.id}" + (
            f" / By {self.creator_dn}" if with_creator_dn and self.creator_dn else ""
        )

    # TODO: use composition class instead of dict
    def get_menu_string_with_composition_status(self, composition: dict):
        return f"{'+' if self.is_in_composition(composition) else ' '} {self.get_displayname()}"

    def __str__(self):
        return self.name if self.name else self.id
    
    