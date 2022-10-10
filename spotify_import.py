import argparse

from src import conf
from src.persistance.track_data import Storage, storage_setup
from src.spotify import spotify_backup
from src.utils.bunch import Bunch

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--liked_fuzzy', action="store_true", help='Try to speed up liked songs import. Do not use if you have un-liked some old liked songs.')
    args = parser.parse_args()
    storage_setup()

    config = Bunch(token=Storage.spotify_token, dump='liked,playlists', format='json', file=conf.playlists_file, liked_fuzzy=args.liked_fuzzy or 1)

    for _ in range(3):
        Storage.spotify_token = spotify_backup.main(config)
        if Storage.spotify_token is not None:
            break

    Storage.save()
