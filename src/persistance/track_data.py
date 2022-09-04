import json
import os

from src import conf

isrc_to_data_default_file = 'isrc_to_data.json'
private_id_prefix = 'HLY'
autogen_detector_version = 1

class SusCode:
    kw_search = 'kw-search'
    isrc_low_lev = 'isrc-low-lev'
    kws_random_first = 'kws-random-first'
    isrc_no_artist_match = 'isrc-no-artist-match'
    isrc_no_match = 'isrc-no-match'
    isrc_error = 'isrc-error'


def shorten(text: str, a=3):
    return text if len(text) < a else text[::len(text) // a]


def describe_track(isrc):
    data = Storage.isrc_to_track_data[isrc]
    return '%s - %s' % (', '.join(data['artists']), data['title'])


class Storage:
    _last_load = None
    _datafile = isrc_to_data_default_file

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
        Storage._last_load = None

        Storage.spotify_token = None
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
    def load_dict(data):
        if 'spotify_token' in data:
            Storage.spotify_token = data['spotify_token']
        Storage.isrc_to_access_url = data['isrc_to_access_url']
        Storage.sus_tracks = data['sus_tracks']
        Storage.is_autogen = data['is_autogen']
        Storage.manual_confirm = data['manual_confirm']
        Storage.isrc_to_track_data = data['isrc_to_track_data']
        if 'metadata_version' in data:
            Storage.metadata_version = data['metadata_version']
        if 'ignored_tracks' in data:
            Storage.ignored_tracks = data['ignored_tracks']
        if 'active_playlist_ids' in data:
            Storage.active_playlist_ids = data['active_playlist_ids']
        if 'isrc_local_downloaded_status' in data:
            Storage.isrc_local_downloaded_status = data['isrc_local_downloaded_status']
        if 'playlist_compositions' in data:
            Storage.playlist_compositions = data['playlist_compositions']

    @staticmethod
    def get_save_dict():
        return {
            'spotify_token': Storage.spotify_token,
            'isrc_to_access_url': Storage.isrc_to_access_url,
            'sus_tracks': Storage.sus_tracks,
            'is_autogen': Storage.is_autogen,
            'manual_confirm': Storage.manual_confirm,
            'isrc_to_track_data': Storage.isrc_to_track_data,
            'metadata_version': Storage.metadata_version,
            'ignored_tracks': Storage.ignored_tracks,
            'active_playlist_ids': Storage.active_playlist_ids,
            'isrc_local_downloaded_status': Storage.isrc_local_downloaded_status,
            'playlist_compositions': Storage.playlist_compositions,
        }

    @staticmethod
    def set_track_data(isrc: str, artists: list, title: str, filename: str):
        Storage.isrc_to_track_data[isrc] = {'artists': artists, 'title': title, 'filename': filename}

    @staticmethod
    def add_sus_track(isrc: str, search_results=None, artists: list = None, title: str = None, code='', data=None):
        if isrc not in Storage.sus_tracks:
            Storage.set_sus_track(isrc, search_results, artists, title, code, data)

    @staticmethod
    def set_sus_track(isrc: str, search_results=None, artists: list = None, title: str = None, code='', data=None):
        Storage.sus_tracks[isrc] = {'code': code, 'title': title, 'artists': artists, 'search_results': search_results,
                                    'data': data}

    @staticmethod
    def ignore_track(isrc: str):
        Storage.ignored_tracks[isrc] = True

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
        Storage.manual_confirm[isrc] = True

    @staticmethod
    def add_access_url(isrc: str, url: str):
        Storage.isrc_to_access_url[isrc] = url
        if isrc in Storage.isrc_local_downloaded_status:
            del Storage.isrc_local_downloaded_status[isrc]

    @staticmethod
    def set_active_playlist(playlist_id: str, active: bool):
        Storage.active_playlist_ids[playlist_id] = active

    @staticmethod
    def is_active_playlist(playlist_id: str):
        return playlist_id in Storage.active_playlist_ids and Storage.active_playlist_ids[playlist_id]

    @staticmethod
    def get_access_url(isrc: str):
        return Storage.isrc_to_access_url[isrc] if isrc in Storage.isrc_to_access_url else None

    @staticmethod
    def set_autogen_track(isrc: str):
        Storage.is_autogen[isrc] = autogen_detector_version

    @staticmethod
    def get_private_isrc(title: str, artists, duration_floor_s: int):
        if isinstance(artists, list):
            return private_id_prefix + shorten(title) + shorten(''.join(artists), a=4) + str(duration_floor_s)
        elif isinstance(artists, str):
            return private_id_prefix + shorten(title) + shorten(artists) + str(duration_floor_s)
        else:
            raise RuntimeError('artists must be string or list')

    @staticmethod
    def load(file=None):
        if file is None:
            file = Storage._datafile
        else:
            Storage._datafile = file
        if os.path.isfile(file):
            f = open(file, "r")
            data = json.loads(f.read())
            Storage.load_dict(data=data)
            Storage._last_load = file
        else:
            print('Data file not found; starting with empty database.')

    @staticmethod
    def save(file=None):
        if file is None:
            file = Storage._datafile
        data = Storage.get_save_dict()
        with open(file, 'w') as f:
            json.dump(data, f)


def add_storage_argparse(parser):
    parser.add_argument('--dev', action='store_true', help='use development database', default=False)
    parser.add_argument('-p', '--profile', type=str, help='data profile name', default='ytfy')


def storage_setup(args):
    development = args.dev
    profile = args.profile
    datafile = '%s_data%s.json' % (profile, '.dev' if development else '')
    Storage.load(datafile)
    conf.Flags.development = development
    conf.Flags.profile = profile
