import argparse
import logging
import colorama

from src import conf
from src.downloader import load_spotify_playlists, init_yt_isrc_tracks, download_playlist, YT, ISRC, download_version
from src.persistance.storage import Storage
from youtubify import is_track_acceptable


def is_file_not_downloaded(track_dict):
    isrc = track_dict[ISRC]
    return Storage.get_download_version(isrc) < download_version


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verify', action='store_true', help='Verify all files exist', default=False)
    parser.add_argument('-t', '--threads', type=int, help='Number of parallel downloads',default=3)
    args = parser.parse_args()
    Storage.storage_setup()

    colorama.init()

    logging.basicConfig(filename='ldownload.log',
                        format="%(asctime)s [%(levelname)s] - %(message)s",
                        level=logging.INFO)
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter(fmt="%(asctime)s [%(levelname)s] - %(message)s"))
    logging.getLogger('').addHandler(console)

    tracks = []
    for isrc in Storage.isrc_to_access_url:
        if is_track_acceptable(isrc):
            tracks.append({YT: Storage.get_access_url(isrc), ISRC: isrc})

    playlists = load_spotify_playlists(conf.playlists_file)

    if not args.verify:
        tracks = list(filter(is_file_not_downloaded, tracks))

    init_yt_isrc_tracks(tracks, playlists)

    download_playlist(tracks, num_threads=args.threads, log_handler=console)

    Storage.save()
    print('Data saved.')
