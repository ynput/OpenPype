from __future__ import print_function

import os
import sys

# only testing dependency for nested modules in package
import six  # noqa


SCRIPT_DIR = os.path.dirname(__file__)
PACKAGE_DIR = os.path.join(SCRIPT_DIR, "modules")
sys.path.append(PACKAGE_DIR)


def flame_panel_executor(selection):
    if "panel_app" in sys.modules.keys():
        print("panel_app module is already loaded")
        del sys.modules["panel_app"]
        import panel_app
        reload(panel_app)  # noqa
        print("panel_app module removed from sys.modules")

    panel_app.FlameBabyPublisherPanel(selection)


def scope_sequence(selection):
    import flame
    return any(isinstance(item, flame.PySequence) for item in selection)


def get_media_panel_custom_ui_actions():
    return [
        {
            "name": "OpenPype: Baby-publisher",
            "actions": [
                {
                    "name": "Create Shots",
                    "isVisible": scope_sequence,
                    "execute": flame_panel_executor
                }
            ]
        }
    ]
