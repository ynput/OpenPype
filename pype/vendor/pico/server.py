import logging
import sys
import socket
import os

from werkzeug.serving import run_simple
from werkzeug.wsgi import SharedDataMiddleware
from werkzeug.utils import import_string

logging.basicConfig(level=logging.INFO)

log = logging.getLogger(__name__)


def run_app(app, **kwargs):
    ip = kwargs.get("ip", '127.0.0.1')
    port = kwargs.get("port", 4242)
    use_debugger = kwargs.get("use_debugger", True)
    use_reloader = kwargs.get("use_reloader", True)
    threaded = kwargs.get("threaded", True)

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

    if ip and ip.startswith('http'):
        ip = ip.replace("http://", "")

    kwargs = {"ip": ip,
              "port": int(os.getenv("PICO_PORT", None)),
              "use_debugger": os.getenv("PICO_DEBUG", None),
              "use_reloader": os.getenv("PICO_RELOADER", None),
              "threaded": os.getenv("PICO_THREADED", None), }

    log.info("Pico.server > settings: "
             "\n\tip: {ip}"
             "\n\tport: {port}"
             "\n\tuse_debugger: {use_debugger}"
             "\n\tuse_reloader: {use_reloader}"
             "\n\tthreaded: {threaded}".format(**kwargs))

    run_app(app, **kwargs)
