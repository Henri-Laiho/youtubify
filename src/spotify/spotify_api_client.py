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

from src.spotify.spotify_api import SpotifyAPI
from src.playlist import Playlist
from src.user import User


logging.basicConfig(level=20, datefmt='%I:%M:%S', format='[%(asctime)s] %(message)s')


def process_tracks(tracks):
    for i in range(len(tracks)):
        track = tracks[i]['track']
        if 'isrc' in track['external_ids']:
            track['external_ids']['isrc'] = track['external_ids']['isrc'].replace('-', '')
    return tracks




# 1 SpotifyApiClient per 1 Spotify user
class SpotifyApiClient:
    def __init__(self, auth_token=None):
        if auth_token:
            self._spotify = SpotifyAPI(auth_token)
        else:
            self._spotify = SpotifyAPI.authorize(client_id='5c098bcc800e45d49e476265bc9b6934',
                                           scope='playlist-read-private playlist-read-collaborative user-library-read')

    def _populate_tracks(self, playlist_json):
        playlist_json['tracks'] = process_tracks(self._spotify.list(playlist['tracks']['href'], {'limit': 100}))

    def _get_playlists_metadata(self):
        logging.info('Loading playlists...')
        playlists_json = self._spotify.list(f'users/{user.id}/playlists', {'limit': 50})
        logging.info(f'Found {len(playlists)} playlists')
        return playlists_json

    def get_changed_playlists(self, user: User):
        playlists = []
        # List liked songs (assume always changed)
        logging.info('Loading liked songs...')
        liked_tracks = self._spotify.list(f'users/{user.id}/tracks', {'limit': 100})
        user.add_playlist(Playlist.from_json({'name': 'Liked Songs', 'id': user.id, 'snapshot_id': None, 'tracks': process_isrc(liked_tracks)}))

        # List all tracks in each playlist
        for playlist_json in self._get_playlists_metadata():
            id = playlist_json['id']
            if id in user.playlist_id_map and playlist_json['snapshot_id'] != user.playlist_id_map[id].snapshot_id:
                logging.info('Reloading playlist: {name} ({tracks[total]} songs)'.format(**playlist))
                self._populate_tracks(playlist_json)
                playlists.append(Playlist.from_json(playlist_json))
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
        me = spotify.get('me', tries=1, on_error='return')
        if not me:
            #TODO: handle properly
            raise RuntimeError("Error when accessing Spotify API")
        logging.info('Logged in as {display_name} ({id})'.format(**me))
        id, display_name = me.id, me.display_name

        return User(id, display_name, self._spotify._auth)
