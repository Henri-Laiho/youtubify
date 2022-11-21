import json
import os
import uuid
from time import time

from src import conf
from src.persistance.old_storage import OldStorage
from src.utils.fs_utils import ensure_dir

private_id_prefix = 'HLY'
autogen_detector_version = 1


def timems():
    return int(time() * 1000)


class SusCode:
    kw_search = 'kw-search'
    isrc_low_lev = 'isrc-low-lev'
    kws_random_first = 'kws-random-first'
    isrc_no_artist_match = 'isrc-no-artist-match'
    isrc_no_match = 'isrc-no-match'
    isrc_error = 'isrc-error'


# TODO: incorporate this into Track class
def shorten(text: str, a=3):
    return text if len(text) < a else text[::len(text) // a]


class Storage:
    _instance_id = None
    _datafile = None

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
        Storage.isrc_to_access_url = {}
        Storage.sus_tracks = {}
        Storage.is_autogen = {}
        Storage.manual_confirm = {}
        Storage.isrc_to_track_data = {}
        Storage.metadata_version = {}
        Storage.ignored_tracks = {}
        Storage.active_playlist_ids = {}
        Storage.isrc_local_downloaded_status = {}
        Storage.playlist_compositions = {}

    @staticmethod
    def load_from_old_storage():
        OldStorage.storage_setup()
        now = timems()
        
        id = str(uuid.uuid4())
        print('Initializing new instance with id', id)
        Storage._instance_id = id

        Storage.isrc_to_access_url = {isrc: (now, OldStorage.isrc_to_access_url[isrc]) for isrc in OldStorage.isrc_to_access_url}
        Storage.sus_tracks = {isrc: (now, OldStorage.sus_tracks[isrc]) for isrc in OldStorage.sus_tracks}
        Storage.is_autogen = {isrc: (now, OldStorage.is_autogen[isrc]) for isrc in OldStorage.is_autogen}
        Storage.manual_confirm = {isrc: (now, OldStorage.manual_confirm[isrc]) for isrc in OldStorage.manual_confirm}
        Storage.isrc_to_track_data = {isrc: (now, OldStorage.isrc_to_track_data[isrc]) for isrc in OldStorage.isrc_to_track_data}
        Storage.ignored_tracks = {isrc: (now, OldStorage.ignored_tracks[isrc]) for isrc in OldStorage.ignored_tracks}
        Storage.active_playlist_ids = OldStorage.active_playlist_ids
        Storage.isrc_local_downloaded_status = OldStorage.isrc_local_downloaded_status
        Storage.playlist_compositions = OldStorage.playlist_compositions
        Storage.metadata_version = OldStorage.metadata_version

    @staticmethod
    def load_private_dict(data):
        if '_instance_id' in data:
            Storage._instance_id = data['_instance_id']
        else:
            id = str(uuid.uuid4())
            print('Initializing new instance with id', id)
            Storage._instance_id = id

        if 'active_playlist_ids' in data:
            Storage.active_playlist_ids = data['active_playlist_ids']
        if 'playlist_compositions' in data:
            Storage.playlist_compositions = data['playlist_compositions']

    @staticmethod
    def load_shared_dict(data):
        if 'isrc_to_access_url' in data:
            Storage.isrc_to_access_url = data['isrc_to_access_url']
        if 'is_autogen' in data:
            Storage.is_autogen = data['is_autogen']
        if 'sus_tracks' in data:
            Storage.sus_tracks = data['sus_tracks']
        if 'manual_confirm' in data:
            Storage.manual_confirm = data['manual_confirm']
        if 'ignored_tracks' in data:
            Storage.ignored_tracks = data['ignored_tracks']
        if 'isrc_to_track_data' in data:
            Storage.isrc_to_track_data = data['isrc_to_track_data']

    @staticmethod
    def load_lib_state_dict(data):
        if 'metadata_version' in data:
            Storage.metadata_version = data['metadata_version']
        if 'isrc_local_downloaded_status' in data:
            Storage.isrc_local_downloaded_status = data['isrc_local_downloaded_status']

    @staticmethod
    def get_private_save_dict():
        return {
            '_instance_id': Storage._instance_id,

            'active_playlist_ids': Storage.active_playlist_ids,
            'playlist_compositions': Storage.playlist_compositions,
        }

    @staticmethod
    def get_shared_save_dict():
        return {
            'isrc_to_access_url': Storage.isrc_to_access_url,
            'is_autogen': Storage.is_autogen,
            'sus_tracks': Storage.sus_tracks,
            'manual_confirm': Storage.manual_confirm,
            'ignored_tracks': Storage.ignored_tracks,
            'isrc_to_track_data': Storage.isrc_to_track_data,
        }

    @staticmethod
    def get_lib_state_save_dict():
        return {
            'metadata_version': Storage.metadata_version,
            'isrc_local_downloaded_status': Storage.isrc_local_downloaded_status,
        }

    @staticmethod
    def set_track_data(isrc: str, artists: list, title: str, filename: str):
        Storage.isrc_to_track_data[isrc] = (timems(), {'artists': artists, 'title': title, 'filename': filename})

    @staticmethod
    def add_sus_track(isrc: str, search_results=None, artists: list = None, title: str = None, code='', data=None):
        if isrc not in Storage.sus_tracks:
            Storage.set_sus_track(isrc, search_results, artists, title, code, data)

    @staticmethod
    def set_sus_track(isrc: str, search_results=None, artists: list = None, title: str = None, code='', data=None):
        Storage.sus_tracks[isrc] = (timems(), {'code': code, 'title': title, 'artists': artists, 'search_results': search_results,
                                    'data': data})

    @staticmethod
    def ignore_track(isrc: str):
        Storage.ignored_tracks[isrc] = (timems(), True)

    @staticmethod
    def reset_track(isrc: str, force=False):
        if not force and isrc in Storage.manual_confirm:
            if input('%s has been manually confirmed. Are you sure you want to reset it? (y/N): ').lower() != 'y':
                return False
        for data in [Storage.manual_confirm, Storage.sus_tracks, Storage.isrc_to_access_url, Storage.is_autogen,
                     Storage.ignored_tracks, Storage.metadata_version, Storage.isrc_local_downloaded_status]:
            if isrc in data:
                del data[isrc]
        return True

    @staticmethod
    def confirm(isrc: str):
        Storage.manual_confirm[isrc] = (timems(), True)

    @staticmethod
    def add_access_url(isrc: str, url: str):
        Storage.isrc_to_access_url[isrc] = (timems(), url)
        if isrc in Storage.isrc_local_downloaded_status:
            del Storage.isrc_local_downloaded_status[isrc]

    @staticmethod
    def set_active_playlist(playlist_id: str, active: bool):
        Storage.active_playlist_ids[playlist_id] = active

    @staticmethod
    def is_active_playlist(playlist_id: str):
        return playlist_id in Storage.active_playlist_ids and Storage.active_playlist_ids[playlist_id]

    @staticmethod
    def is_manual_confirm(isrc: str):
        return Storage.manual_confirm[isrc][1] if isrc in Storage.manual_confirm else False

    @staticmethod
    def is_track_ignored(isrc: str):
        return Storage.ignored_tracks[isrc][1] if isrc in Storage.ignored_tracks else False

    @staticmethod
    def get_access_url(isrc: str):
        return Storage.isrc_to_access_url[isrc][1] if isrc in Storage.isrc_to_access_url else None

    @staticmethod
    def get_sus_track(isrc: str):
        return Storage.sus_tracks[isrc][1] if isrc in Storage.sus_tracks else None

    @staticmethod
    def get_track_data(isrc: str):
        return Storage.isrc_to_track_data[isrc][1] if isrc in Storage.isrc_to_track_data else None

    @staticmethod
    def set_autogen_track(isrc: str):
        Storage.is_autogen[isrc] = (timems(), autogen_detector_version)

    @staticmethod
    def get_private_isrc(title: str, artists, duration_floor_s: int):
        if isinstance(artists, list):
            return private_id_prefix + shorten(title) + shorten(''.join(artists), a=4) + str(duration_floor_s)
        elif isinstance(artists, str):
            return private_id_prefix + shorten(title) + shorten(artists) + str(duration_floor_s)
        else:
            raise RuntimeError('artists must be string or list')

    @staticmethod
    def load_private(filename):
        if os.path.isfile(filename):
            with open(filename, 'r') as f:
                data = json.loads(f.read())
            Storage.load_private_dict(data=data)
        else:
            print('Private data file not found; starting with empty database.')

    @staticmethod
    def load_shared(filename):
        if os.path.isfile(filename):
            with open(filename, 'r') as f:
                data = json.loads(f.read())
            Storage.load_shared_dict(data=data)
        else:
            print('Shared data file not found; starting with empty database.')

    @staticmethod
    def load_lib_state(filename):
        if os.path.isfile(filename):
            with open(filename, 'r') as f:
                data = json.loads(f.read())
            Storage.load_lib_state_dict(data=data)
        else:
            print('Library state data file not found; starting with empty database.')

    @staticmethod
    def load(filename=None):
        if filename is None:
            filename = Storage._datafile
        else:
            Storage._datafile = filename

        if os.path.isdir(conf.data_folder):
            private_path = os.path.join(conf.data_folder, filename)
            Storage.load_private(private_path + '_private.json')
            Storage.load_shared(private_path + '_shared.json')
            Storage.load_lib_state(private_path + '_lib_state.json')
        else:
            Storage.load_from_old_storage()

    @staticmethod
    def save(file=None):
        if file is None:
            file = Storage._datafile

        private_path = os.path.join(conf.data_folder, file)
        sync_folder = os.path.join(conf.data_folder, 'sync', Storage._instance_id)
        ensure_dir(sync_folder)
        sync_path = os.path.join(sync_folder, file)

        data_private = Storage.get_private_save_dict()
        with open(private_path + '_private.json', 'w') as f:
            json.dump(data_private, f)

        data_shared = Storage.get_shared_save_dict()
        with open(private_path + '_shared.json', 'w') as f:
            json.dump(data_shared, f)
        with open(sync_path +'_shared.json', 'w') as f:
            json.dump(data_shared, f)

        data_lib_state = Storage.get_lib_state_save_dict()
        with open(private_path + '_lib_state.json', 'w') as f:
            json.dump(data_lib_state, f)

    @staticmethod
    def storage_setup():
        datafile = 'ytfy_data'
        Storage.load(datafile)
