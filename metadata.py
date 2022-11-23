import argparse
import os

import music_tag
import wget as wget
from music_tag import Artwork, MetadataItem

from src import conf
from src.track import Track
from src.downloader import load_spotify_playlists, ISRC_MAP
from src.persistance.storage import Storage
from src.persistance.cli_storage import CliStorage
from src.spotify.spotify_backup import SpotifyAPI
from src.utils.fs_utils import ensure_dir, get_filename_ext
from youtubify import is_track_acceptable

metadata_version = 5


def fetch_genre_data(spotify_urls):
    if CliStorage.spotify_token:
        spotify = SpotifyAPI(CliStorage.spotify_token)
    else:
        spotify = SpotifyAPI.authorize(client_id='5c098bcc800e45d49e476265bc9b6934',
                                       scope='playlist-read-private playlist-read-collaborative user-library-read')
        CliStorage.spotify_token = spotify._auth
    for x in spotify_urls:
        spotify.get('tracks/%s' % x)
    # not supported by api
    raise NotImplementedError


def set_metadata_field(metadata, field, data):
    if isinstance(data, list):
        if data is not None and len(data) > 0:
            metadata[field] = data[0]
            for x in data[1:]:
                metadata.append_tag(field, x)
    else:
        metadata[field] = data


def get_metadata_field(file, field):
    return music_tag.load_file(file)[field]


def is_comment_field_good(file):
    comment = get_metadata_field(file, 'comment')
    if isinstance(comment.val, str):
        return 'Added' in comment.val and 'isrc=' in comment.val
    return False


def set_metadata(file, title, album, albumartists, artists, track_number, total_tracks, disc_number, comments,
                 art_files, year):
    f = music_tag.load_file(file)
    f['title'] = title
    f['album'] = album
    f['tracknumber'] = track_number
    f['totaltracks'] = total_tracks
    f['discnumber'] = disc_number
    f['year'] = year
    set_metadata_field(f, 'albumartist', albumartists)
    set_metadata_field(f, 'artist', artists)
    set_metadata_field(f, 'comment', comments)
    arts = []
    for x, width, height in art_files:
        with open(x, 'rb') as img_in:
            art = img_in.read()
            arts.append(Artwork(art, width=width, height=height, fmt='jpeg', depth=24))
    key = 'artwork'
    tmap = f.tag_map[key]
    md_type = tmap.type
    md_sanitizer = tmap.sanitizer
    f[key] = MetadataItem(md_type, md_sanitizer, arts)

    f.save()


def download_arts(urls, track_file):
    ensure_dir(conf.downloaded_artwork_folder)
    arts = []
    for i, url in enumerate(urls[:1]):
        filename = os.path.join(conf.downloaded_artwork_folder, track_file + ' cover ' + str(i + 1) + '.jpg')
        exists = os.path.isfile(filename)
        if not exists:
            wget.download(url['url'], filename, bar=None)
        arts.append((filename, url['width'], url['height']))
    return arts


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--check_comment', action='store_true', help='Check comment field to estimate if metadata is present', default=False)
    args = parser.parse_args()
    CliStorage.storage_setup()
    Storage.storage_setup()

    playlists = load_spotify_playlists(conf.playlists_file)

    i = 0
    for isrc in Storage.isrc_to_track_data:
        i += 1
        print('\rAdding Metadata: %d/%d' % (i, len(Storage.isrc_to_track_data)), end='')
        if is_track_acceptable(isrc):
            track_data = Storage.get_track_data(isrc)
            newfilename = track_data['filename']
            fnext = get_filename_ext(newfilename, conf.downloaded_audio_folder)
            newpath_ext = None
            if fnext is not None:
                newpath_ext = os.path.join(conf.downloaded_audio_folder, fnext)

            if newpath_ext is not None and os.path.isfile(newpath_ext):
                pass
            else:
                print('\nWARNING: track "%s" missing' % newfilename)
                continue

            if args.check_comment:
                if not is_comment_field_good(newpath_ext):
                    Storage.set_metadata_version(isrc, -1)
            if Storage.get_metadata_version(isrc) >= metadata_version:
                continue

            track = None
            for playlist in playlists:
                if isrc in playlist.isrc_map:
                    track = playlist.isrc_map[isrc]
                    break
            if track is None:
                continue

            art_files = download_arts(track.arts, newfilename)

            set_metadata(newpath_ext,
                         title=track.name,
                         album=track.album_name,
                         albumartists=track.album_artists,
                         artists=track.artists,
                         track_number=track.track_number,
                         total_tracks=track.album_total_tracks,
                         disc_number=track.disc_number,
                         comments=['Added %s; isrc=%s' % (track.date_added + ' ' + track.time_added, isrc)],
                         art_files=art_files, year=track.release[:None if '-' not in track.release else track.release.index('-')])

            for x, _, _ in art_files:
                os.remove(x)

            Storage.set_metadata_version(isrc, metadata_version)
    print('\nDone')
    Storage.save()
