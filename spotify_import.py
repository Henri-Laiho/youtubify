import argparse

from src import conf
from src.persistance.track_data import Storage, storage_setup
from src.spotify import spotify_backup
from src.utils.bunch import Bunch

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    args = parser.parse_args()
    storage_setup()

    for _ in range(3):
        args2 = Bunch(token=Storage.spotify_token, dump='liked,playlists,rm_dash_in_isrc', format='json', file=conf.playlists_file)
        Storage.spotify_token = spotify_backup.main(args2)
        if Storage.spotify_token is not None:
            break

    Storage.save()
