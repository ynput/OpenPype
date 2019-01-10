import os
import sys
import pico
# from pico.decorators import request_args, prehandle
from pico import PicoApp
from pico import client

from avalon import api as avalon
from avalon import io

import pyblish.api as pyblish

from app.api import forward
from pype import api as pype

# remove all Handlers created by pico
for name, handler in [(handler.get_name(), handler)
                      for handler in pype.Logger.logging.root.handlers[:]]:
    if "pype" not in str(name).lower():
        pype.Logger.logging.root.removeHandler(handler)

log = pype.Logger.getLogger(__name__, "aport")


SESSION = avalon.session
if not SESSION:
    io.install()


@pico.expose()
def publish(json_data_path):
    log.warning("avalon.session is: \n{}".format(SESSION))
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


@pico.expose()
def context(project, asset, task, app):
    # http://localhost:4242/pipeline/context?project=this&asset=shot01&task=comp

    os.environ["AVALON_PROJECT"] = project

    avalon.update_current_task(task, asset, app)

    project_code = pype.get_project_code()
    pype.set_project_code(project_code)
    hierarchy = pype.get_hierarchy()
    pype.set_hierarchy(hierarchy)
    SESSION.update({"AVALON_HIERARCHY": hierarchy,
                    "AVALON_PROJECTCODE": project_code,
                    "current_dir": os.getcwd()
                    })

    return SESSION


@pico.expose()
def deregister_plugin_path():
    if os.getenv("PUBLISH_PATH", None):
        aport_plugin_path = [p.replace("\\", "/") for p in os.environ["PUBLISH_PATH"].split(
            os.pathsep) if "aport" in p][0]
        os.environ["PUBLISH_PATH"] = aport_plugin_path
    else:
        log.warning("deregister_plugin_path(): No PUBLISH_PATH is registred")

    return "Publish path deregistered"


@pico.expose()
def register_plugin_path(publish_path):
    deregister_plugin_path()
    if os.getenv("PUBLISH_PATH", None):
        os.environ["PUBLISH_PATH"] = os.pathsep.join(
            os.environ["PUBLISH_PATH"].split(os.pathsep) +
            [publish_path.replace("\\", "/")]
        )
    else:
        os.environ["PUBLISH_PATH"] = publish_path
    log.warning(os.environ["PUBLISH_PATH"].split(os.pathsep))
    return "Publish registered paths: {}".format(
        os.environ["PUBLISH_PATH"].split(os.pathsep)
    )


app = PicoApp()
app.register_module(__name__)
