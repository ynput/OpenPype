import logging
import sys
import os

MAYA_STANDALONE = False
try:
    import maya.standalone
    maya.standalone.initialize()
    MAYA_STANDALONE = True
    print("maya standalone initialized")
except RuntimeError:
    pass

import pyblish.util   # noqa: E402
from maya import cmds   # noqa: E402


def setup_pyblish_logging():
    log = logging.getLogger("pyblish")
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "pyblish (%(levelname)s) (line: %(lineno)d) %(name)s:"
        "\n%(message)s"
    )
    handler.setFormatter(formatter)
    log.addHandler(handler)


def _run_publish_test_deferred():
    try:
        setup_pyblish_logging()

        if MAYA_STANDALONE:
            print("Opening " + os.environ["AVALON_LAST_WORKFILE"])
            cmds.file(
                os.environ["AVALON_LAST_WORKFILE"], open=True, force=True
            )

        pyblish.util.publish()
    finally:
        cmds.quit(force=True)


cmds.evalDeferred("_run_publish_test_deferred()", lowestPriority=True)
