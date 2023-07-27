import sys
import os
import logging

sys.stderr = sys.stdout

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
    # Fetch the logger Pyblish uses for all of its messages
    log = logging.getLogger("pyblish")

    # Do what `basicConfig` does, except explicitly
    # and with control over where and how messages go
    hnd = logging.StreamHandler()
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

    cmds.evalDeferred("setup_pyblish_logging()", evaluateNext=True)
    cmds.evalDeferred(
        "import pyblish.util;pyblish.util.publish()", lowestPriority=True
    )

    print("finished OpenPype usersetup for testing")
    if not os.environ.get("KEEP_APP_OPEN") or not MAYA_STANDALONE:
        cmds.evalDeferred("cmds.quit(force=True)", lowestPriority=True)


main()
