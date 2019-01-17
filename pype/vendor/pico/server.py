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
    ip = kwargs.get("ip")
    port = kwargs.get("port")
    use_debugger = kwargs.get("use_debugger")
    use_reloader = kwargs.get("use_reloader")
    threaded = kwargs.get("threaded")
    html_dir = kwargs.get("html_dir")
    log.info("html_dir: {}".format(html_dir))
    app = SharedDataMiddleware(app, html_dirs)
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

    html_dirs = os.getenv("PICO_HTML_DIR") or None
    if html_dirs:
        html_dirs = {"/{}".format(os.path.basename(p)): p.replace("\\", "/")
                     for p in html_dirs.split(os.pathsep)}

    log.info("> html_dirs: {}".format(html_dirs))
    ip = os.getenv("PICO_IP", '127.0.0.1')

    if ip and ip.startswith('http'):
        ip = ip.replace("http://", "")

    kwargs = {"ip": ip,
              "port": int(os.getenv("PICO_PORT", 4242)),
              "use_debugger": os.getenv("PICO_DEBUG", True),
              "use_reloader": os.getenv("PICO_RELOADER", True),
              "threaded": os.getenv("PICO_THREADED", True),
              "html_dir": html_dirs}

    log.info("Pico.server > settings: "
             "\n\thtml_dir: {html_dir}"
             "\n\tip: {ip}"
             "\n\tport: {port}"
             "\n\tuse_debugger: {use_debugger}"
             "\n\tuse_reloader: {use_reloader}"
             "\n\tthreaded: {threaded}".format(**kwargs))

    run_app(app, **kwargs)
