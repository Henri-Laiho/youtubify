import json
import os

from src import conf
from src.utils.fs_utils import ensure_dir


class CliStorage:
    _last_load = None
    _datafile = None

    user_displayname = None
    user_id = None
    spotify_token = None

    @staticmethod
    def reset():
        CliStorage._last_load = None

        CliStorage.user_displayname = None
        CliStorage.user_id = None
        CliStorage.spotify_token = None

    @staticmethod
    def load_dict(data):
        if 'user_displayname' in data:
            CliStorage.user_displayname = data['user_displayname']
        if 'user_id' in data:
            CliStorage.user_id = data['user_id']
        if 'spotify_token' in data:
            CliStorage.spotify_token = data['spotify_token']

    @staticmethod
    def get_save_dict():
        return {
            'user_displayname': CliStorage.user_displayname,
            'user_id': CliStorage.user_id,
            'spotify_token': CliStorage.spotify_token,
        }

    @staticmethod
    def load(filename=None):
        if filename is None:
            filename = CliStorage._datafile
        else:
            CliStorage._datafile = filename
        if os.path.isfile(filename):
            with open(filename, 'r') as f:
                data = json.loads(f.read())
            CliStorage.load_dict(data=data)
            CliStorage._last_load = filename
        else:
            print('Cli data file not found; starting with empty database.')

    @staticmethod
    def save(file=None):
        if file is None:
            file = CliStorage._datafile
        data = CliStorage.get_save_dict()
        ensure_dir(conf.data_folder)
        with open(file, 'w') as f:
            json.dump(data, f)

    @staticmethod
    def storage_setup():
        datafile = os.path.join(conf.data_folder, 'cli_data.json')
        CliStorage.load(datafile)
