import argparse

from src import conf
from src.persistance.cli_storage import CliStorage
from src.spotify import spotify_backup
from src.utils.bunch import Bunch

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--liked_fuzzy', action="store_true", help='Try to speed up liked songs import. Do not use if you have un-liked some old liked songs.')
    args = parser.parse_args()
    CliStorage.storage_setup()

    for _ in range(3):
        config = Bunch(token=CliStorage.spotify_token, dump='liked,playlists', format='json', file=conf.playlists_file, liked_fuzzy=args.liked_fuzzy or 1)
        CliStorage.spotify_token, CliStorage.user_id, CliStorage.user_displayname = spotify_backup.main(config)
        
        if CliStorage.spotify_token is not None:
            break

    CliStorage.save()
