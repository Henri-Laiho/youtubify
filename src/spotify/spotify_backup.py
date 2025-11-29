# playlists.json --format=json --dump=liked,playlists

import codecs
import http.client
import http.server
import json
import logging
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
import os
import secrets
import string
import hashlib
import base64
from urllib.parse import urlparse, parse_qs

from src import conf

logging.basicConfig(level=20, datefmt='%I:%M:%S', format='[%(asctime)s] %(message)s')


def generate_code_verifier(length: int = 64) -> str:
    # Length must be between 43 and 128
    if not (43 <= length <= 128):
        raise ValueError("code_verifier length must be between 43 and 128")

    charset = string.ascii_letters + string.digits + "-._~"
    return ''.join(secrets.choice(charset) for _ in range(length))


def generate_code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    # URL-safe base64, strip '=' padding
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode("ascii")


CLIENT_ID = '5c098bcc800e45d49e476265bc9b6934'
CODE_VERIFIER = generate_code_verifier()
CODE_CHALLENGE = generate_code_challenge(CODE_VERIFIER)

print("code_verifier:", CODE_VERIFIER)
print("code_challenge:", CODE_CHALLENGE)

class SpotifyAPI:

    # Requires an OAuth token.
    def __init__(self, auth):
        self._auth = auth

    @staticmethod
    def exchange_code_for_token(code: str) -> str:
        data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': f'http://127.0.0.1:{SpotifyAPI._SERVER_PORT}/redirect',
            'client_id': CLIENT_ID,
            'code_verifier': CODE_VERIFIER,  # same one you used to build the challenge
        }
        body = urllib.parse.urlencode(data).encode('utf-8')

        req = urllib.request.Request(
            'https://accounts.spotify.com/api/token',
            data=body,
            method='POST',
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        with urllib.request.urlopen(req, timeout=15) as res:
            token_response = json.load(res)
        return token_response['access_token']

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
            'response_type': 'code',
            'client_id': client_id,
            'scope': scope,
            'redirect_uri': f'http://127.0.0.1:{SpotifyAPI._SERVER_PORT}/redirect',
            'code_challenge_method': 'S256',
            'code_challenge': CODE_CHALLENGE,
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
            if self.path.startswith('/redirect'):
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)

                if 'error' in params:
                    logging.error(f"Spotify auth error: {params['error'][0]}")
                    self.send_error(400)
                    return

                code = params.get('code', [None])[0]
                if not code:
                    logging.error(f"No code in redirect URL: {self.path}")
                    self.send_error(400)
                    return

                access_token = SpotifyAPI.exchange_code_for_token(code)

                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(
                    b'<script>close()</script>Thanks! You may now close this window.'
                )

                logging.info(f"Received access token from Spotify: {access_token}")
                raise SpotifyAPI._Authorization(access_token)

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
        spotify = SpotifyAPI.authorize(client_id=CLIENT_ID,
                                       scope='playlist-read-private playlist-read-collaborative user-library-read')

    # Get the ID of the logged in user.
    logging.info('Loading user info...')
    me = spotify.get('me', tries=1, on_error='return')
    if me is None:
        return None, None, None
    logging.info('Logged in as {display_name} ({id})'.format(**me))

    old_playlist_id_map = {}
    if os.path.isfile(conf.playlists_file):
        with open(conf.playlists_file, "r") as f:
            old_playlists = json.loads(f.read())
            for playlist in old_playlists:
                playlist['isrc_map'] = {get_isrc(x) : x for x in playlist['tracks'] if has_isrc(x)}
            old_playlist_id_map = {playlist['id'] : playlist for playlist in old_playlists}

    liked_fuzzy = args.liked_fuzzy and old_playlist_id_map and me['id'] in old_playlist_id_map
    reload = args.reload
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
                                                         url='me/tracks',
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
            if reload or id not in old_playlist_id_map or playlist_json['snapshot_id'] != old_playlist_id_map[id]['snapshot_id']:
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
