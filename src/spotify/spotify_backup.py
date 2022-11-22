# playlists.json --format=json --dump=liked,playlists

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
import os

from src import conf

logging.basicConfig(level=20, datefmt='%I:%M:%S', format='[%(asctime)s] %(message)s')


class SpotifyAPI:

    # Requires an OAuth token.
    def __init__(self, auth):
        self._auth = auth

    # Gets a resource from the Spotify API and returns the object.
    def get(self, url, params={}, tries=25, on_error='exit'):
        # Construct the correct URL.
        if not url.startswith('https://api.spotify.com/v1/'):
            url = 'https://api.spotify.com/v1/' + url
        if params:
            url += ('&' if '?' in url else '?') + urllib.parse.urlencode(params)

        # Try the sending off the request a specified number of times before giving up.
        for tri in range(tries):
            try:
                req = urllib.request.Request(url)
                req.add_header('Authorization', 'Bearer ' + self._auth)
                res = urllib.request.urlopen(req, timeout=15)
                reader = codecs.getreader('utf-8')
                return json.load(reader(res))
            except Exception as err:
                logging.info('Couldn\'t load URL: {} ({})'.format(url, err))
                time.sleep(2 + 0.35*tri)
                if tri+1 < tries:
                    logging.info('Trying again... (%d/%d)' % (tri+1, tries))
        if on_error == 'exit':
            logging.critical('Failed after %d tries. Aborting spotify import!' % (tries))
            sys.exit(1)
        return None

    # The Spotify API breaks long lists into multiple pages. This method automatically
    # fetches all pages and joins them, returning in a single list of objects.
    def list(self, url, params={}, get_should_continue=None):
        last_log_time = time.time()
        response = self.get(url, params)
        items = response['items']

        while response['next'] and (get_should_continue is None or get_should_continue(items)):
            if time.time() > last_log_time + 1:
                last_log_time = time.time()
                logging.info(f"Loaded {len(items)}/{response['total']} items")

            response = self.get(response['next'])
            items += response['items']
        if response['next']:
            logging.info(f"Stopping at {len(items)}/{response['total']} items")
        return items

    # Pops open a browser window for a user to log in and authorize API access.
    @staticmethod
    def authorize(client_id, scope):
        url = 'https://accounts.spotify.com/authorize?' + urllib.parse.urlencode({
            'response_type': 'token',
            'client_id': client_id,
            'scope': scope,
            'redirect_uri': 'http://127.0.0.1:{}/redirect'.format(SpotifyAPI._SERVER_PORT)
        })
        logging.info(f'Logging in (click if it doesn\'t open automatically): {url}')
        webbrowser.open(url)

        # Start a simple, local HTTP server to listen for the authorization token... (i.e. a hack).
        server = SpotifyAPI._AuthorizationServer('127.0.0.1', SpotifyAPI._SERVER_PORT)
        try:
            while True:
                server.handle_request()
        except SpotifyAPI._Authorization as auth:
            return SpotifyAPI(auth.access_token)

    # The port that the local server listens on. Don't change this,
    # as Spotify only will redirect to certain predefined URLs.
    _SERVER_PORT = 43019

    class _AuthorizationServer(http.server.HTTPServer):
        def __init__(self, host, port):
            http.server.HTTPServer.__init__(self, (host, port), SpotifyAPI._AuthorizationHandler)

        # Disable the default error handling.
        def handle_error(self, request, client_address):
            raise

    class _AuthorizationHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            # The Spotify API has redirected here, but access_token is hidden in the URL fragment.
            # Read it using JavaScript and send it to /token as an actual query string...
            if self.path.startswith('/redirect'):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<script>location.replace("token?" + location.hash.slice(1));</script>')

            # Read access_token and use an exception to kill the server listening...
            elif self.path.startswith('/token?'):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<script>close()</script>Thanks! You may now close this window.')

                access_token = re.search('access_token=([^&]*)', self.path).group(1)
                logging.info(f'Received access token from Spotify: {access_token}')
                raise SpotifyAPI._Authorization(access_token)

            else:
                self.send_error(404)

        # Disable the default logging.
        def log_message(self, format, *args):
            pass

    class _Authorization(Exception):
        def __init__(self, access_token):
            self.access_token = access_token

def has_isrc(track_json):
    return 'isrc' in track_json['track']['external_ids']


def get_isrc(track_json):
    return track_json['track']['external_ids']['isrc']


def set_isrc(track_json, isrc):
    track_json['track']['external_ids']['isrc'] = isrc


def main(args):
    # If they didn't give a filename, then just prompt them. (They probably just double-clicked.)
    while not args.file:
        args.file = input('Enter a file name (e.g. playlists.txt): ')
        args.format = args.file.split('.')[-1]

    # Log into the Spotify API.
    if args.token:
        spotify = SpotifyAPI(args.token)
    else:
        spotify = SpotifyAPI.authorize(client_id='5c098bcc800e45d49e476265bc9b6934',
                                       scope='playlist-read-private playlist-read-collaborative user-library-read')

    # Get the ID of the logged in user.
    logging.info('Loading user info...')
    me = spotify.get('me', tries=1, on_error='return')
    if me is None:
        return None, None, None
    logging.info('Logged in as {display_name} ({id})'.format(**me))

    old_playlists = None
    old_playlist_id_map = {}
    if os.path.isfile(conf.playlists_file):
        with open(conf.playlists_file, "r") as f:
            old_playlists = json.loads(f.read())
            for playlist in old_playlists:
                playlist['isrc_map'] = {get_isrc(x) : x for x in playlist['tracks'] if has_isrc(x)}
            old_playlist_id_map = {playlist['id'] : playlist for playlist in old_playlists}

    liked_fuzzy = args.liked_fuzzy and old_playlist_id_map and me['id'] in old_playlist_id_map
    playlists = []

    def process_tracks(tracks):
        for i in range(len(tracks)):
            if 'isrc' in tracks[i]['track']['external_ids']:
                isrc = tracks[i]['track']['external_ids']['isrc']
                tracks[i]['track']['external_ids']['isrc'] = isrc.replace('-', '')
            del tracks[i]['track']['available_markets']
            del tracks[i]['track']['album']['available_markets']
        return tracks

    def populate_tracks_and_make_playlist(playlist_json, url: str, fuzzy_with_playlist=None):
        data = {'new_items_idx': 0}
        if fuzzy_with_playlist:
            def should_continue(tracks_json):
                slice_start = data['new_items_idx']
                data['new_items_idx'] = len(tracks_json)
                for new_track_json in tracks_json[slice_start:]:
                    if not has_isrc(new_track_json) or get_isrc(new_track_json) not in fuzzy_with_playlist['isrc_map']:
                        return True
                return False
        else:
            should_continue = None
        tracks = process_tracks(spotify.list(url, {'limit': 50}, should_continue))
        if fuzzy_with_playlist:
            new_tracks = list(filter(lambda x: not has_isrc(x) or get_isrc(x) not in fuzzy_with_playlist['isrc_map'], tracks))
            playlist_json['tracks'] = new_tracks + fuzzy_with_playlist['tracks']
        else:
            playlist_json['tracks'] = tracks
        return playlist_json

    # List liked songs
    if 'liked' in args.dump:
        logging.info('Loading liked songs...')
        liked_tracks = populate_tracks_and_make_playlist({'name': 'Liked Songs', 'id': me['id'], 'snapshot_id': None}, 
                                                         url='users/{user_id}/tracks'.format(user_id=me['id']),
                                                         fuzzy_with_playlist=old_playlist_id_map[me['id']] if liked_fuzzy else None)
        playlists += [liked_tracks]

    # List all playlists and the tracks in each playlist
    if 'playlists' in args.dump:
        logging.info('Loading playlists...')
        playlists_json = spotify.list('users/{user_id}/playlists'.format(user_id=me['id']), {'limit': 50})
        logging.info(f'Found {len(playlists_json)} playlists')

        # List all tracks in each playlist
        for playlist_json in playlists_json:
            id = playlist_json['id']
            if id not in old_playlist_id_map or playlist_json['snapshot_id'] != old_playlist_id_map[id]['snapshot_id']:
                logging.info('Reloading playlist: {name} ({tracks[total]} songs)'.format(**playlist_json))
                populate_tracks_and_make_playlist(playlist_json, playlist_json['tracks']['href'])
            else:
                playlist_json['tracks'] = old_playlist_id_map[id]['tracks']
        playlists += playlists_json

    # Write the file.
    logging.info('Writing files...')
    with open(args.file, 'w', encoding='utf-8') as f:
        # JSON file.
        if args.format == 'json':
            json.dump(playlists, f)
    logging.info('Wrote file: ' + args.file)
    return spotify._auth, me['id'], me['display_name']
