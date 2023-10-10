import logging
import sys

from maya import cmds

import pyblish.util


def setup_pyblish_logging():
    log = logging.getLogger("pyblish")
    hnd = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter(
        "pyblish (%(levelname)s) (line: %(lineno)d) %(name)s:"
        "\n%(message)s"
    )
    hnd.setFormatter(fmt)
    log.addHandler(hnd)


def _run_publish_test_deferred():
    try:
        pyblish.util.publish()
    finally:
        cmds.quit(force=True)


cmds.evalDeferred("setup_pyblish_logging()", evaluateNext=True)
cmds.evalDeferred("_run_publish_test_deferred()", lowestPriority=True)
