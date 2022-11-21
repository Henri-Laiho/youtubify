import json
import os

from src import conf
from src.utils.fs_utils import ensure_dir


class OldStorage:
    _last_load = None
    _datafile = None

    spotify_token = None
    isrc_to_access_url = {}
    sus_tracks = {}
    is_autogen = {}
    manual_confirm = {}
    isrc_to_track_data = {}
    metadata_version = {}
    ignored_tracks = {}
    active_playlist_ids = {}
    isrc_local_downloaded_status = {}
    playlist_compositions = {}

    @staticmethod
    def reset():
        OldStorage._last_load = None

        OldStorage.spotify_token = None
        OldStorage.isrc_to_access_url = {}
        OldStorage.sus_tracks = {}
        OldStorage.is_autogen = {}
        OldStorage.manual_confirm = {}
        OldStorage.isrc_to_track_data = {}
        OldStorage.metadata_version = {}
        OldStorage.ignored_tracks = {}
        OldStorage.active_playlist_ids = {}
        OldStorage.isrc_local_downloaded_status = {}
        OldStorage.playlist_compositions = {}

    @staticmethod
    def load_dict(data):
        if 'spotify_token' in data:
            OldStorage.spotify_token = data['spotify_token']
        OldStorage.isrc_to_access_url = data['isrc_to_access_url']
        OldStorage.sus_tracks = data['sus_tracks']
        OldStorage.is_autogen = data['is_autogen']
        OldStorage.manual_confirm = data['manual_confirm']
        OldStorage.isrc_to_track_data = data['isrc_to_track_data']
        if 'metadata_version' in data:
            OldStorage.metadata_version = data['metadata_version']
        if 'ignored_tracks' in data:
            OldStorage.ignored_tracks = data['ignored_tracks']
        if 'active_playlist_ids' in data:
            OldStorage.active_playlist_ids = data['active_playlist_ids']
        if 'isrc_local_downloaded_status' in data:
            OldStorage.isrc_local_downloaded_status = data['isrc_local_downloaded_status']
        if 'playlist_compositions' in data:
            OldStorage.playlist_compositions = data['playlist_compositions']

    @staticmethod
    def get_save_dict():
        return {
            'spotify_token': OldStorage.spotify_token,
            'isrc_to_access_url': OldStorage.isrc_to_access_url,
            'sus_tracks': OldStorage.sus_tracks,
            'is_autogen': OldStorage.is_autogen,
            'manual_confirm': OldStorage.manual_confirm,
            'isrc_to_track_data': OldStorage.isrc_to_track_data,
            'metadata_version': OldStorage.metadata_version,
            'ignored_tracks': OldStorage.ignored_tracks,
            'active_playlist_ids': OldStorage.active_playlist_ids,
            'isrc_local_downloaded_status': OldStorage.isrc_local_downloaded_status,
            'playlist_compositions': OldStorage.playlist_compositions,
        }

    @staticmethod
    def load(filename=None):
        if filename is None:
            filename = OldStorage._datafile
        else:
            OldStorage._datafile = filename
        if os.path.isfile(filename):
            with open(filename, 'r') as f:
                data = json.loads(f.read())
            OldStorage.load_dict(data=data)
            OldStorage._last_load = filename
        else:
            print('Data file not found; starting with empty database.')

    @staticmethod
    def save(file=None):
        if file is None:
            file = OldStorage._datafile
        data = OldStorage.get_save_dict()
        with open(file, 'w') as f:
            json.dump(data, f)


    @staticmethod
    def storage_setup():
        datafile = 'ytfy_data.json'
        OldStorage.load(datafile)
