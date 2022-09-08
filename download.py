import argparse
import logging
import colorama

from src import conf
from src.downloader import load_spotify_playlists, init_yt_isrc_tracks, download_playlist, YT, ISRC, download_version
from src.persistance.track_data import Storage, add_storage_argparse, storage_setup
from youtubify import is_track_acceptable


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    add_storage_argparse(parser)
    parser.add_argument('-v', '--verify', action='store_true', help='Verify all files exist', default=False)
    args = parser.parse_args()
    storage_setup(args)

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
            tracks.append({YT: Storage.isrc_to_access_url[isrc], ISRC: isrc})

    playlists = load_spotify_playlists(conf.playlists_file)

    init_yt_isrc_tracks(tracks, playlists)


    if not args.verify:
        new_tracks = []
        for track in tracks:
            isrc = track[ISRC]
            yt = track[YT]
            if isrc not in Storage.isrc_local_downloaded_status or Storage.isrc_local_downloaded_status[isrc] < download_version:
                new_tracks.append(track)
        tracks = new_tracks

    download_playlist(tracks, num_threads=16, log_handler=console)

    Storage.save()
