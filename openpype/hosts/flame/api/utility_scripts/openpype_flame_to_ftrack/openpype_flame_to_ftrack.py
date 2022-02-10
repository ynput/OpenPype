from __future__ import print_function

import os
import sys

try:
    import six  # noqa
except ImportError as msg:
    raise ImportError("Cannot import this module: {}".format(msg)) from msg

SCRIPT_DIR = os.path.dirname(__file__)
PACKAGE_DIR = os.path.join(SCRIPT_DIR, "modules")
sys.path.append(PACKAGE_DIR)


def flame_panel_executor(selection):
    if "panel_app" in sys.modules.keys():
        print("panel_app module is already loaded")
        del sys.modules["panel_app"]
        print("panel_app module removed from sys.modules")

    import panel_app
    panel_app.FlameToFtrackPanel(selection)


def scope_sequence(selection):
    import flame
    return any(isinstance(item, flame.PySequence) for item in selection)


def get_media_panel_custom_ui_actions():
    return [
        {
            "name": "OpenPype: Ftrack",
            "actions": [
                {
                    "name": "Create Shots",
                    "isVisible": scope_sequence,
                    "execute": flame_panel_executor
                }
            ]
        }
    ]
