import http
import secrets


class SpotifyAuthSerice(threading.Thread):
    _client_id = '5c098bcc800e45d49e476265bc9b6934',
    _scope = 'playlist-read-private playlist-read-collaborative user-library-read'
    # The port that the local server listens on. Don't change this,
    # as Spotify only will redirect to certain predefined URLs.
    _SERVER_PORT = 43019

    def __init__(self):
        self._should_exit = False
        self._server = SpotifyAuthSerice._AuthorizationServer('127.0.0.1', SpotifyAuthSerice._SERVER_PORT)

    def run(self):
        try:
            while not self._should_exit:
                self._server.handle_request()
        except SpotifyAPI._Authorization as auth:
            return SpotifyAPI(auth.access_token)

    def stop():
        self._should_exit = True

    def get_login_url(youtubify_token: str):
        return 'https://accounts.spotify.com/authorize?' + urllib.parse.urlencode({
            'response_type': 'token',
            'client_id': SpotifyAuthSerice._client_id,
            'scope': SpotifyAuthSerice._scope,
            'redirect_uri': 'http://127.0.0.1:{}/redirect/{}'.format(SpotifyAuthSerice._SERVER_PORT, youtubify_token)
        })
        #webbrowser.open(url)
        
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
