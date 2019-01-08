import logging
import sys
import socket
import os

from werkzeug.serving import run_simple
from werkzeug.wsgi import SharedDataMiddleware
from werkzeug.utils import import_string

logging.basicConfig(level=logging.INFO)

log = logging.getLogger(__name__)


def run_app(app, ip='127.0.0.1', port=4242, use_debugger=True, use_reloader=True, threaded=True):
    app = SharedDataMiddleware(app, {
        '/': 'static'
    })
    while True:
        try:
            run_simple(ip, port, app, use_debugger=use_debugger,
                       use_reloader=use_reloader, threaded=threaded)
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

    ip = os.getenv("PICO_IP", None)
    port = int(os.getenv("PICO_PORT", None))
    use_debugger = os.getenv("PICO_DEBUG", None)
    use_reloader = os.getenv("PICO_RELOADER", None)
    threaded = os.getenv("PICO_THREADED", None)
    log.info(type(port))
    log.info("Pico.server > settings: "
             "\n\tip: {0}"
             "\n\tport: {1}"
             "\n\tuse_debugger: {2}"
             "\n\tuse_reloader: {3}"
             "\n\tthreaded: {4}".format(
                 ip, port, use_debugger, use_reloader, threaded
             ))

    run_app(app, ip=ip, port=port, use_debugger=use_debugger,
            use_reloader=use_reloader, threaded=threaded)
