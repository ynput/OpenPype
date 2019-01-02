import logging
import sys
import socket

from werkzeug.serving import run_simple
from werkzeug.wsgi import SharedDataMiddleware
from werkzeug.utils import import_string

logging.basicConfig(level=logging.INFO)


def run_app(app, ip='127.0.0.1', port=4242, use_debugger=True, use_reloader=True, threaded=True):
    app = SharedDataMiddleware(app, {
        '/': 'static'
    })
    while True:
        try:
            run_simple(ip, port, app, use_debugger=use_debugger, use_reloader=use_reloader, threaded=threaded)
            break
        except (OSError, socket.error):
            port += 1


if __name__ == '__main__':
    sys.path.insert(0, '.')
    if len(sys.argv) > 1:
        module_name = sys.argv[1]
        module_name = module_name.split('.py')[0]
        if ':' not in module_name:
            module_name += ':app'
        app = import_string(module_name)
    run_app(app)
