import werkzeug.exceptions
from werkzeug.exceptions import *


class Unauthorized(werkzeug.exceptions.Unauthorized):
    """ Overridden to return WWW-Authenticate challenge header """
    def get_headers(self, environ):
        return [('Content-Type', 'text/html'),
                ('WWW-Authenticate', 'Basic realm="Login required"')]
