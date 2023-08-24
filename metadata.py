import argparse
import os

import music_tag
import wget as wget
from music_tag import Artwork, MetadataItem
from mutagen import MutagenError

from src import conf
from src.downloader import load_spotify_playlists
from src.persistance.storage import Storage
from src.persistance.cli_storage import CliStorage
from src.spotify.spotify_backup import SpotifyAPI
from src.utils.fs_utils import ensure_dir, get_filename_ext
from youtubify import is_track_acceptable

metadata_version = 5
DAY_MS = 24 * 60 * 60 * 1000

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
        if len(data) > 0:
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


def set_metadata(file, title=None, album=None, albumartists=None, artists=None, track_number=None, total_tracks=None,
                 disc_number=None, comments=None, art_files=None, year=None):
    try:
        f = music_tag.load_file(file)
        if title is not None:
            f['title'] = title
        if album is not None:
            f['album'] = album
        if track_number is not None:
            f['tracknumber'] = track_number
        if total_tracks is not None:
            f['totaltracks'] = total_tracks
        if disc_number is not None:
            f['discnumber'] = disc_number
        if year is not None:
            f['year'] = year
        if albumartists is not None:
            set_metadata_field(f, 'albumartist', albumartists)
        if artists is not None:
            set_metadata_field(f, 'artist', artists)
        if comments is not None:
            set_metadata_field(f, 'comment', comments)
        if art_files is not None:
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
    except MutagenError:
        print(f'\nFailed to update metadata for {file}')


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


def should_force_playlist_belonging_update(args):
    if not args.playlist_belonging:
        return False
    if args.interval:
        return Storage.get_time_since_lib_playlist_belonging_last_updated_ms() > args.interval * DAY_MS
    return True


def get_track_and_belongings(isrc, playlists):
    belonging_to = []
    for playlist in playlists:
        if isrc in playlist.isrc_map:
            belonging_to.append(playlist)
    belonging_to.sort(key=lambda it: len(it.tracks))
    track = belonging_to[-1].isrc_map[isrc] if len(belonging_to) else None
    belongings = [it.get_displayname() for it in belonging_to]
    return track, belongings


def build_comment(isrc, track, belongings):
    added = track.date_added + ' ' + track.time_added
    return [f'Added {added}; isrc={isrc}; In {len(belongings):<4} playlists: {", ".join(belongings)}']


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--check_comment', action='store_true', help='Check comment field to estimate if metadata is present', default=False)
    parser.add_argument('-p', '--playlist_belonging', action='store_true', help='Force playlist belonging information update', default=False)
    parser.add_argument('-i', '--interval', type=int, help='Minimum interval days to update playlist belongings', default=None)
    args = parser.parse_args()
    CliStorage.storage_setup()
    Storage.storage_setup()

    playlist_belonging_update = should_force_playlist_belonging_update(args)
    if playlist_belonging_update:
        Storage.set_lib_playlist_belonging_updated()
        print('Forcing playlist belonging update.')

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
                if playlist_belonging_update:
                    track, belongings = get_track_and_belongings(isrc, playlists)
                    if track is None:
                        continue
                    set_metadata(newpath_ext, comments=build_comment(isrc, track, belongings))
                continue
            track, belongings = get_track_and_belongings(isrc, playlists)
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
                         comments=build_comment(isrc, track, belongings),
                         art_files=art_files,
                         year=track.release[:None if '-' not in track.release else track.release.index('-')])

            for x, _, _ in art_files:
                os.remove(x)

            Storage.set_metadata_version(isrc, metadata_version)
    print('\nDone')
    Storage.save()
