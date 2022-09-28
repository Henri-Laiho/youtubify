import argparse
import codecs
import http.client
import http.server
import json
import logging
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from copy import copy

from src.spotify.spotify_api import SpotifyAPI
from src.playlist import Playlist
from src.track import Track
from src.user import User


logging.basicConfig(level=20, datefmt='%I:%M:%S', format='[%(asctime)s] %(message)s')


def has_isrc(track_json):
    return 'isrc' in track_json['track']['external_ids']


def get_isrc(track_json):
    return track_json['track']['external_ids']['isrc']


def set_isrc(track_json, isrc):
    track_json['track']['external_ids']['isrc'] = isrc


def process_tracks(tracks):
    for i in range(len(tracks)):
        track = tracks[i]
        if has_isrc(track):
            set_isrc(track, get_isrc(track).replace('-', ''))
    return tracks


# 1 SpotifyApiClient per 1 Spotify user
class SpotifyApiClient:
    def __init__(self, auth_token=None):
        if auth_token:
            self._spotify = SpotifyAPI(auth_token)
        else:
            self._spotify = SpotifyAPI.authorize(client_id='5c098bcc800e45d49e476265bc9b6934',
                                           scope='playlist-read-private playlist-read-collaborative user-library-read')

    def _populate_tracks_and_make_playlist(self, playlist_json, url: str, fuzzy_with_playlist: Playlist=None):
        new_items_idx = 0
        if fuzzy_with_playlist:
            def should_continue(tracks_json):
                slice_start = new_items_idx
                new_items_idx = len(tracks_json)
                for new_track_json in tracks_json[slice_start:]:
                    if not has_isrc(new_track_json) or get_isrc(new_track_json) not in fuzzy_with_playlist.isrc_map:
                        return True
                return False
        else:
            should_continue = None
        tracks = process_tracks(self._spotify.list(url, {'limit': 100}, should_continue))
        if fuzzy_with_playlist:
            new_tracks = list(map(Track.from_spotify_json, 
                                  filter(lambda x: not has_isrc(x) or get_isrc(x) not in fuzzy_with_playlist.isrc_map, tracks)))
            if len(new_tracks) == 0:
                return None
            playlist = copy(fuzzy_with_playlist)
            playlist.tracks = new_tracks + fuzzy_with_playlist.tracks
            return playlist
        else:
            playlist_json['tracks'] = tracks
            return Playlist.from_json(playlist_json)

    def _get_playlists_metadata(self):
        logging.info('Loading playlists...')
        playlists_json = self._spotify.list(f'users/{user.id}/playlists', {'limit': 50})
        logging.info(f'Found {len(playlists)} playlists')
        return playlists_json

    def get_changed_playlists(self, user: User, fuzzy_liked_songs: bool=True, fuzzy_playlists: bool=False, rescan: bool=False):
        playlists = []
        # List liked songs (assume always changed)
        logging.info('Loading liked songs...')
        liked_songs = self._populate_tracks_and_make_playlist({'name': 'Liked Songs', 'id': user.id, 'snapshot_id': None}, f'users/{user.id}/tracks', user.get_liked_songs() if fuzzy_liked_songs else None)
        if liked_songs:
            playlists.append(liked_songs)

        # List all tracks in each playlist
        for playlist_json in self._get_playlists_metadata():
            id = playlist_json['id']
            if rescan or id in user.playlist_id_map and playlist_json['snapshot_id'] != user.playlist_id_map[id].snapshot_id:
                logging.info('Reloading playlist: {name} ({tracks[total]} songs)'.format(**playlist))
                playlist = self._populate_tracks_and_make_playlist(playlist_json, playlist_json['tracks']['href'], user.playlist_id_map[id] if fuzzy_playlists else None)
                if playlist:
                    playlists.append(playlist)
        return playlists

    def get_new_playlists(self, user: User):
        playlists = []
        for playlist_json in self._get_playlists_metadata():
            if playlist_json['id'] not in user.playlist_id_map:
                logging.info('Loading new playlist: {name} ({tracks[total]} songs)'.format(**playlist))
                self._populate_tracks(playlist_json)
                playlists.append(Playlist.from_json(playlist_json))
        return playlists
        
    def get_user(self):
        # Get the ID of the logged in user.
        logging.info('Loading user info...')
        me = spotify.get('me', tries=3, on_error='return')
        if not me:
            #TODO: handle properly
            raise RuntimeError("Error when accessing Spotify API")
        logging.info('Logged in as {display_name} ({id})'.format(**me))

        return User(me['id'], me['display_name'], self._spotify._auth)
