import os
import sys
import pico
from pico import PicoApp

from app.api import forward
from pype import api as pype

# remove all Handlers created by pico
for name, handler in [(handler.get_name(), handler)
                      for handler in pype.Logger.logging.root.handlers[:]]:
    if "pype" not in str(name).lower():
        pype.Logger.logging.root.removeHandler(handler)

log = pype.Logger.getLogger(__name__, "editorial")


@pico.expose()
def publish(json_data_path):
    # load json_data_path; add context into data; damp
    # create empty temp/json_data_get
    # run standalone pyblish
    pype_start = os.path.join(os.getenv('PYPE_SETUP_ROOT'),
                              "app", "pype-start.py")

    args = [pype_start, "--publish",
            "-pp", os.environ["PUBLISH_PATH"],
            "-d", "json_context_data_path", json_data_path
            ]

    log.info(args)

    # start standalone pyblish qml
    forward([
        sys.executable, "-u"
    ] + args,
        cwd=os.getenv('PYPE_SETUP_ROOT')
    )

    return {"json_back": "this/json/file"}


app = PicoApp()
app.register_module(__name__)
