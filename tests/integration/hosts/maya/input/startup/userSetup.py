import logging
import sys

from maya import cmds


def setup_pyblish_logging():
    log = logging.getLogger("pyblish")
    hnd = logging.StreamHandler(sys.stdout)
    fmt = logging.Formatter(
        "pyblish (%(levelname)s) (line: %(lineno)d) %(name)s:"
        "\n%(message)s"
    )
    hnd.setFormatter(fmt)
    log.addHandler(hnd)


def main():
    cmds.evalDeferred("setup_pyblish_logging()", evaluateNext=True)
    cmds.evalDeferred(
        "import pyblish.util;pyblish.util.publish()", lowestPriority=True
    )
    cmds.evalDeferred("cmds.quit(force=True)", lowestPriority=True)


main()
