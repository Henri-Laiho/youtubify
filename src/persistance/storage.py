import json
import os
import uuid
from time import time

from src import conf
from src.persistance.old_storage import OldStorage
from src.persistance.cli_storage import CliStorage
from src.utils.fs_utils import ensure_dir

DAY_MS = 1000 * 60 * 60 * 24

private_id_prefix = 'HLY'
autogen_detector_version = 1
folder_id_file = '.id'


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


def is_newer(local_item: tuple, incoming_item: tuple) -> bool:
    return local_item[0] < incoming_item[0]


def import_table(local_table: dict, incoming_table: dict, new_key_monitor: set = None):
    for item_key in incoming_table:
        if item_key not in local_table or is_newer(local_table[item_key], incoming_table[item_key]):
            local_table[item_key] = incoming_table[item_key]
            if new_key_monitor is not None:
                new_key_monitor.add(item_key)


def get_folder_id(folder, message='Initializing new folder with id %s', current_id=None):
    id_path = os.path.join(folder, folder_id_file)
    if os.path.isfile(id_path):
        with open(id_path, 'r') as f:
            return f.read()
    else:
        id = str(uuid.uuid4()) if current_id is None else current_id
        print(message % id + ' (current)' if id == current_id else '')
        ensure_dir(folder)
        with open(id_path, 'w') as f:
            f.write(id)
        return id


def get_folder_data(folder, data_key):
    path = os.path.join(folder, '.' + data_key)
    if os.path.isfile(path):
        with open(path, 'r') as f:
            return f.read()
    return None


class Storage:
    __new_key_monitor = None

    _instance_id = None
    _datafile = None
    _spotify_user_service = None

    isrc_to_access_url = {}
    sus_tracks = {}
    is_autogen = {}
    manual_confirm = {}
    isrc_to_track_data = {}
    metadata_version = {}
    lib_state_meta = {
        'playlist_belonging_update_time': (0, 0),
    }
    ignored_tracks = {}
    active_playlist_ids = {}
    isrc_local_downloaded_status = {}
    url_download_errors = {}
    playlist_compositions = {}
    download_library_id = None
    private_data_update_time = 0
    youtube_api_daily_requests = {'reset_time': timems(), 'count': 0}

    @staticmethod
    def reset():
        Storage.isrc_to_access_url = {}
        Storage.sus_tracks = {}
        Storage.is_autogen = {}
        Storage.manual_confirm = {}
        Storage.isrc_to_track_data = {}
        Storage.metadata_version = {}
        Storage.lib_state_meta = {
            'playlist_belonging_update_time': (0, 0),
        }
        Storage.ignored_tracks = {}
        Storage.active_playlist_ids = {}
        Storage.isrc_local_downloaded_status = {}
        Storage.url_download_errors = {}
        Storage.playlist_compositions = {}
        Storage.download_library_id = None
        Storage.private_data_update_time = 0
        Storage.youtube_api_daily_requests = {'reset_time': timems(), 'count': 0}

    @staticmethod
    def load_from_old_storage():
        OldStorage.storage_setup()
        now = 0
        
        id = str(uuid.uuid4())
        print('Initializing new instance with id', id)
        Storage._instance_id = id

        Storage.isrc_to_access_url = {isrc: (now, OldStorage.isrc_to_access_url[isrc]) for isrc in OldStorage.isrc_to_access_url}
        Storage.sus_tracks = {isrc: (now, OldStorage.sus_tracks[isrc]) for isrc in OldStorage.sus_tracks}
        Storage.is_autogen = {isrc: (now, OldStorage.is_autogen[isrc]) for isrc in OldStorage.is_autogen}
        Storage.manual_confirm = {isrc: (now, OldStorage.manual_confirm[isrc]) for isrc in OldStorage.manual_confirm}
        Storage.isrc_to_track_data = {isrc: (now, OldStorage.isrc_to_track_data[isrc]) for isrc in OldStorage.isrc_to_track_data}
        Storage.ignored_tracks = {isrc: (now, OldStorage.ignored_tracks[isrc]) for isrc in OldStorage.ignored_tracks}
        Storage.isrc_local_downloaded_status = {isrc: (now, OldStorage.isrc_local_downloaded_status[isrc]) for isrc in OldStorage.isrc_local_downloaded_status}
        Storage.metadata_version = {isrc: (now, OldStorage.metadata_version[isrc]) for isrc in OldStorage.metadata_version}
        Storage.active_playlist_ids = OldStorage.active_playlist_ids
        Storage.playlist_compositions = OldStorage.playlist_compositions
        Storage.private_data_update_time = now
        Storage.youtube_api_daily_requests = {'reset_time': timems(), 'count': 0}

    @staticmethod
    def get_private_save_dict():
        return {
            'private_data_update_time' : Storage.private_data_update_time,
            'active_playlist_ids': Storage.active_playlist_ids,
            'playlist_compositions': Storage.playlist_compositions,
            'youtube_api_daily_requests': Storage.youtube_api_daily_requests,
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
            'url_download_errors': Storage.url_download_errors,
        }

    @staticmethod
    def get_lib_state_save_dict():
        return {
            'metadata_version': Storage.metadata_version,
            'isrc_local_downloaded_status': Storage.isrc_local_downloaded_status,
            'META': Storage.lib_state_meta,
        }

    @staticmethod
    def load_private_dict(data):
        if 'private_data_update_time' in data:
            Storage.private_data_update_time = data['private_data_update_time']
        if '_instance_id' in data:  # TODO: remove when no instances with this version
            Storage._instance_id = data['_instance_id']

        if 'active_playlist_ids' in data:
            Storage.active_playlist_ids = data['active_playlist_ids']
        if 'playlist_compositions' in data:
            Storage.playlist_compositions = data['playlist_compositions']
        if 'youtube_api_daily_requests' in data:
            Storage.youtube_api_daily_requests = data['youtube_api_daily_requests']

    @staticmethod
    def load_shared_dict(data):
        local_db = Storage.get_shared_save_dict()
        for key in local_db:
            if key in data:
                local_db[key].update(data[key])

    @staticmethod
    def load_lib_state_dict(data):
        local_db = Storage.get_lib_state_save_dict()
        for key in local_db:
            if key in data:
                local_db[key].update(data[key])

    @staticmethod
    def sync_data():
        Storage.__new_key_monitor = set()
        for file, local_db, import_method in [
            (Storage._get_shared_filename(), Storage.get_shared_save_dict(), Storage.import_data), 
            (Storage._get_private_filename(), Storage.get_private_save_dict(), Storage.import_private_data), 
            (Storage._get_lib_state_filename(), Storage.get_lib_state_save_dict(), Storage.import_data)]:
            for folder in conf.data_export_folders:
                files = list(filter(lambda it: os.path.isfile(it), (os.path.join(folder, x, file) for x in os.listdir(folder) if x != Storage._instance_id)))
                Storage.import_files(files, local_db, import_method)
        print('Sync complete - imported data on %d tracks.' % len(Storage.__new_key_monitor))
        Storage.__new_key_monitor = None

    @staticmethod
    def import_files(files: list, local_db: dict, import_method):
        for file in files:
            with open(file, 'r') as f:
                data = json.loads(f.read())
            import_method([data], local_db)

    @staticmethod
    def import_data(dicts: list, local_db: dict):
        for table_key in local_db:
            for db in dicts:
                if  table_key in db:
                    import_table(local_db[table_key], db[table_key], Storage.__new_key_monitor)

    @staticmethod
    def import_private_data(private_dicts: list, _):
        for db in private_dicts:
            if Storage.private_data_update_time < db['private_data_update_time']:
                Storage.private_data_update_time = db['private_data_update_time']
                if 'active_playlist_ids' in db:
                    Storage.active_playlist_ids = db['active_playlist_ids']
                if 'playlist_compositions' in db:
                    Storage.playlist_compositions = db['playlist_compositions']
                if 'youtube_api_daily_requests' in db:
                    Storage.youtube_api_daily_requests = db['youtube_api_daily_requests']

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
        Storage.reset_download_errors(isrc, Storage.get_access_url(isrc))


    @staticmethod
    def add_access_url(isrc: str, url: str):
        Storage.isrc_to_access_url[isrc] = (timems(), url)
        if isrc in Storage.isrc_local_downloaded_status:
            del Storage.isrc_local_downloaded_status[isrc]

    @staticmethod
    def add_download_error(isrc: str, url: str):
        if isrc not in Storage.url_download_errors:
            Storage.url_download_errors[isrc] = (timems(), {})
        if url not in Storage.url_download_errors[isrc][1]:
            Storage.url_download_errors[isrc][1][url] = 0
        Storage.url_download_errors[isrc][1][url] += 1

    @staticmethod
    def get_download_errors(isrc: str, url: str):
        if isrc in Storage.url_download_errors and url in Storage.url_download_errors[isrc][1]:
            return Storage.url_download_errors[isrc][1][url]
        return 0

    @staticmethod
    def reset_download_errors(isrc: str, url: str):
        if isrc in Storage.url_download_errors and url in Storage.url_download_errors[isrc][1]:
            del Storage.url_download_errors[isrc][1][url]
            Storage.url_download_errors[isrc][0] = timems()

    @staticmethod
    def set_active_playlist(playlist_id: str, active: bool):
        Storage.private_data_update_time = timems()
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
    def get_download_version(isrc: str):
        return Storage.isrc_local_downloaded_status[isrc][1] if isrc in Storage.isrc_local_downloaded_status else -1

    @staticmethod
    def get_metadata_version(isrc: str):
        return Storage.metadata_version[isrc][1] if isrc in Storage.metadata_version else -1

    @staticmethod
    def get_youtube_daily_request_count():
        reset_time = Storage.youtube_api_daily_requests['reset_time']
        if timems() - reset_time > DAY_MS:
            Storage.youtube_api_daily_requests['count'] = 0
        return Storage.youtube_api_daily_requests['count']

    @staticmethod
    def add_youtube_daily_request(amount=1):
        Storage.youtube_api_daily_requests['count'] = Storage.get_youtube_daily_request_count() + amount

    @staticmethod
    def set_metadata_version(isrc: str, version: int):
        Storage.metadata_version[isrc] = (timems(), version)

    @staticmethod
    def set_download_version(isrc: str, version: int):
        Storage.isrc_local_downloaded_status[isrc] = (timems(), version)

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
    def get_time_since_lib_playlist_belonging_last_updated_ms():
        return timems() - Storage.lib_state_meta['playlist_belonging_update_time'][1]

    @staticmethod
    def set_lib_playlist_belonging_updated():
        Storage.lib_state_meta['playlist_belonging_update_time'] = (timems(), timems())

    @staticmethod
    def set_composition(key, comp):
        Storage.private_data_update_time = timems()
        Storage.playlist_compositions[key] = comp

    @staticmethod
    def remove_composition(key):
        Storage.private_data_update_time = timems()
        del Storage.playlist_compositions[key]

    @staticmethod
    def _get_shared_filename():
        return Storage._datafile + '_shared.json'

    @staticmethod
    def _get_private_filename():
        uid = Storage._spotify_user_service.get_spotify_user_id()
        return Storage._datafile + '_' + (uid if uid is not None else 'anonymous') + '_private.json'

    @staticmethod
    def _get_lib_state_filename():
        return Storage._datafile + '_' + Storage.download_library_id + '_lib_state.json'

    @staticmethod
    def load_private(filename):
        if os.path.isfile(filename):
            with open(filename, 'r') as f:
                data = json.loads(f.read())
            Storage.load_private_dict(data)
        else:
            print('Private data file not found; starting with empty database.')

    @staticmethod
    def load_shared(filename):
        if os.path.isfile(filename):
            with open(filename, 'r') as f:
                data = json.loads(f.read())
            Storage.load_shared_dict(data)
        else:
            print('Shared data file not found; starting with empty database.')

    @staticmethod
    def load_lib_state(filename):
        if os.path.isfile(filename):
            with open(filename, 'r') as f:
                data = json.loads(f.read())
            Storage.load_lib_state_dict(data)
        else:
            print('Library state data file not found; starting with empty database.')

    @staticmethod
    def load(filename=None):
        if filename is None:
            filename = Storage._datafile
        else:
            Storage._datafile = filename

        Storage.download_library_id = get_folder_id(conf.downloaded_audio_folder, 'Initializing audio library with id %s')

        if os.path.isfile(os.path.join(conf.data_folder, Storage._get_private_filename())):
            Storage.load_private(os.path.join(conf.data_folder, Storage._get_private_filename()))
            Storage.load_shared(os.path.join(conf.data_folder, Storage._get_shared_filename()))
            Storage.load_lib_state(os.path.join(conf.data_folder, Storage._get_lib_state_filename()))
            Storage._instance_id = get_folder_id(conf.data_folder, 'Initializing new instance with id %s', Storage._instance_id)
        else:
            Storage.load_from_old_storage()

    @staticmethod
    def save(file=None):
        if file is None:
            file = Storage._datafile

        sync_folders = [os.path.join(x, Storage._instance_id) for x in conf.data_export_folders]
        for x in sync_folders: ensure_dir(x)

        data_private = Storage.get_private_save_dict()
        data_shared = Storage.get_shared_save_dict()
        data_lib_state = Storage.get_lib_state_save_dict()

        with open(os.path.join(conf.data_folder, Storage._get_private_filename()), 'w') as f:
            json.dump(data_private, f)
        with open(os.path.join(conf.data_folder, Storage._get_shared_filename()), 'w') as f:
            json.dump(data_shared, f)
        with open(os.path.join(conf.data_folder, Storage._get_lib_state_filename()), 'w') as f:
            json.dump(data_lib_state, f)

        for sync_folder in sync_folders:
            with open(os.path.join(sync_folder, Storage._get_private_filename()), 'w') as f:
                json.dump(data_private, f)
            with open(os.path.join(sync_folder, Storage._get_shared_filename()), 'w') as f:
                json.dump(data_shared, f)
            with open(os.path.join(sync_folder, Storage._get_lib_state_filename()), 'w') as f:
                json.dump(data_lib_state, f)

    @staticmethod
    def storage_setup(spotify_user_service = CliStorage):
        datafile = 'ytfy_data'
        Storage._spotify_user_service = spotify_user_service
        Storage.load(datafile)
