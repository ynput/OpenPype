import os
import sys

from avalon import api, pipeline

PACKAGE_DIR = os.path.dirname(__file__)
PLUGINS_DIR = os.path.join(PACKAGE_DIR, "plugins", "launcher")
ACTIONS_DIR = os.path.join(PLUGINS_DIR, "actions")


def register_launcher_actions():
    """Register specific actions which should be accessible in the launcher"""

    actions = []
    ext = ".py"
    sys.path.append(ACTIONS_DIR)

    for f in os.listdir(ACTIONS_DIR):
        file, extention = os.path.splitext(f)
        if ext in extention:
            module = __import__(file)
            klass = getattr(module, file)
            actions.append(klass)

    if actions is []:
        return

    for action in actions:
        print("Using launcher action from config @ '{}'".format(action.name))
        pipeline.register_plugin(api.Action, action)
