from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib import parse
import webbrowser
import functools
import threading
from openpype import resources


class LoginServerHandler(BaseHTTPRequestHandler):
    '''Login server handler.'''

    message_filepath = resources.get_resource("ftrack", "sign_in_message.html")

    def __init__(self, login_callback, *args, **kw):
        '''Initialise handler.'''
        self.login_callback = login_callback
        BaseHTTPRequestHandler.__init__(self, *args, **kw)

    def log_message(self, format_str, *args):
        """Override method of BaseHTTPRequestHandler.

        Goal is to use `print` instead of `sys.stderr.write`
        """
        # Change
        print("%s - - [%s] %s\n" % (
            self.client_address[0],
            self.log_date_time_string(),
            format_str % args
        ))

    def do_GET(self):
        '''Override to handle requests ourselves.'''
        parsed_path = parse.urlparse(self.path)
        query = parsed_path.query

        api_user = None
        api_key = None
        login_credentials = None
        if 'api_user' and 'api_key' in query:
            login_credentials = parse.parse_qs(query)
            api_user = login_credentials['api_user'][0]
            api_key = login_credentials['api_key'][0]

            with open(self.message_filepath, "r") as message_file:
                sign_in_message = message_file.read()

            # formatting html code for python
            replacements = (
                ("{", "{{"),
                ("}", "}}"),
                ("{{}}", "{}")
            )
            for replacement in (replacements):
                sign_in_message = sign_in_message.replace(*replacement)
            message = sign_in_message.format(api_user)
        else:
            message = "<h1>Failed to sign in</h1>"

        self.send_response(200)
        self.end_headers()
        self.wfile.write(message.encode())

        if login_credentials:
            self.login_callback(
                api_user,
                api_key
            )


class LoginServerThread(threading.Thread):
    '''Login server thread.'''

    def __init__(self, url, callback):
        self.url = url
        self.callback = callback
        self._server = None
        super(LoginServerThread, self).__init__()

    def _handle_login(self, api_user, api_key):
        '''Login to server with *api_user* and *api_key*.'''
        self.callback(api_user, api_key)

    def stop(self):
        if self._server:
            self._server.server_close()

    def run(self):
        '''Listen for events.'''
        self._server = HTTPServer(
            ('localhost', 0),
            functools.partial(
                LoginServerHandler, self._handle_login
            )
        )
        unformated_url = (
            '{0}/user/api_credentials?''redirect_url=http://localhost:{1}'
        )
        webbrowser.open_new_tab(
            unformated_url.format(
                self.url, self._server.server_port
            )
        )
        self._server.handle_request()
