import os
import logging
import sys

MAYA_STANDALONE = False
try:
    import maya.standalone
    maya.standalone.initialize()
    MAYA_STANDALONE = True
    print("maya standalone initialized")
except RuntimeError:
    pass

from maya import cmds  # noqa: E402


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
    if MAYA_STANDALONE:
        setup_pyblish_logging()

        cmds.file(os.environ["AVALON_LAST_WORKFILE"], open=True, force=True)

        import pyblish.util
        pyblish.util.publish()

        return

    if not bool(os.environ.get("KEEP_APP_OPEN")):
        cmds.evalDeferred("setup_pyblish_logging()", evaluateNext=True)
        cmds.evalDeferred(
            "import pyblish.util;pyblish.util.publish()", lowestPriority=True
        )

    if not bool(os.environ.get("KEEP_APP_OPEN")) and not MAYA_STANDALONE:
        cmds.evalDeferred("cmds.quit(force=True)", lowestPriority=True)


main()
