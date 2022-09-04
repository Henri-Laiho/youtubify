import argparse
import os

import music_tag
import wget as wget
from music_tag import Artwork, MetadataItem

from src import conf
from src.downloader import load_spotify_playlists, ISRC_MAP
from src.persistance.track_data import Storage, add_storage_argparse, storage_setup
from src.spotify.spotify_backup import SpotifyAPI
from src.ytdownload import ensure_dir, get_filename_ext
from youtubify import is_track_acceptable

metadata_version = 4


def fetch_genre_data(spotify_urls):
    if Storage.spotify_token:
        spotify = SpotifyAPI(Storage.spotify_token)
    else:
        spotify = SpotifyAPI.authorize(client_id='5c098bcc800e45d49e476265bc9b6934',
                                       scope='playlist-read-private playlist-read-collaborative user-library-read')
        Storage.spotify_token = spotify._auth
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
    for i, url in enumerate(urls):
        filename = os.path.join(conf.downloaded_artwork_folder, track_file + ' cover ' + str(i + 1) + '.jpg')
        exists = os.path.isfile(filename)
        if not exists:
            wget.download(url['url'], filename, bar=None)
        arts.append((filename, url['width'], url['height']))
    return arts


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    add_storage_argparse(parser)
    args = parser.parse_args()
    storage_setup(args)

    playlists = load_spotify_playlists(conf.playlists_file)

    i = 0
    for isrc in Storage.isrc_to_track_data:
        i += 1
        print('\rAdding Metadata: %d/%d' % (i, len(Storage.isrc_to_track_data)), end='')
        if is_track_acceptable(isrc):
            track = Storage.isrc_to_track_data[isrc]
            name = track['title']
            artists = track['artists']
            if 'filename' not in track:
                continue
            newfilename = track['filename']
            fnext = get_filename_ext(newfilename, conf.downloaded_audio_folder)
            newpath_ext = None
            if fnext is not None:
                newpath_ext = os.path.join(conf.downloaded_audio_folder, fnext)

            if newpath_ext is not None and os.path.isfile(newpath_ext):
                pass
            else:
                print('\nWARNING: track "%s" missing' % newfilename)
                continue

            if isrc in Storage.metadata_version and Storage.metadata_version[isrc] >= metadata_version:
                continue

            strack = None
            for playlist in playlists:
                if isrc in playlist[ISRC_MAP]:
                    strack = playlist[ISRC_MAP][isrc]
                    break
            if strack is None:
                continue

            st_track = strack['track']
            added_at = strack['added_at']
            album = st_track['album']
            release = album['release_date']
            art_urls = album['images']
            art_files = download_arts(art_urls, newfilename)
            date_added = added_at[:added_at.index('T')]
            time_added = added_at[added_at.index('T') + 1:-1]

            set_metadata(newpath_ext,
                         title=name,
                         album=album['name'],
                         albumartists=[x['name'] for x in album['artists']],
                         artists=artists,
                         track_number=st_track['track_number'],
                         total_tracks=album['total_tracks'],
                         disc_number=st_track['disc_number'],
                         comments=['Added %s; isrc=%s' % (date_added + ' ' + time_added, isrc)],
                         art_files=art_files, year=release[:None if '-' not in release else release.index('-')])

            for x, _, _ in art_files:
                os.remove(x)

            Storage.metadata_version[isrc] = metadata_version
    print('\nDone')
    Storage.save()
