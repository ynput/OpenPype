import os

import logging

from maya import cmds


def setup_logging():
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


print("starting OpenPype usersetup for testing")
cmds.evalDeferred("setup_logging()", evaluateNext=True)
cmds.evalDeferred(
    "import pyblish.util;pyblish.util.publish()", lowestPriority=True
)

print("finished OpenPype usersetup for testing")
if not os.environ.get("KEEP_APP_OPEN"):
    cmds.evalDeferred("cmds.quit(force=True)", lowestPriority=True)
