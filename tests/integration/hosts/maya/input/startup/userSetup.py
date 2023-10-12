import logging
import sys

from maya import cmds

import pyblish.util


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
        pyblish.util.publish()
    finally:
        cmds.quit(force=True)


cmds.evalDeferred("_run_publish_test_deferred()", lowestPriority=True)
