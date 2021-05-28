import argparse

from src import conf
from src.downloader import load_spotify_playlists, init_yt_isrc_tracks, download_playlist, YT, ISRC
from src.persistance.track_data import Storage, add_storage_argparse, storage_setup
from youtubify import is_track_acceptable

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    add_storage_argparse(parser)
    args = parser.parse_args()
    storage_setup(args)

    tracks = []
    for isrc in Storage.isrc_to_access_url:
        if is_track_acceptable(isrc):
            tracks.append({YT: Storage.isrc_to_access_url[isrc], ISRC: isrc})

    playlists = load_spotify_playlists(conf.playlists_file)

    init_yt_isrc_tracks(tracks, playlists)

    download_playlist(tracks, num_threads=5)
