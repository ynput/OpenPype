import os
import sys
import hiero.core
from pypeapp import Logger
from avalon.api import Session
from hiero.ui import findMenuAction

# this way we secure compatibility between nuke 10 and 11
try:
    from PySide.QtGui import *
except Exception:
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

from .tags import add_tags_from_presets

from .lib import (
    reload_config,
    set_workfiles
)

log = Logger().get_logger(__name__, "nukestudio")

self = sys.modules[__name__]
self._change_context_menu = None


def _update_menu_task_label(*args):
    """Update the task label in Avalon menu to current session"""

    object_name = self._change_context_menu
    found_menu = findMenuAction(object_name)

    if not found_menu:
        log.warning("Can't find menuItem: {}".format(object_name))
        return

    label = "{}, {}".format(Session["AVALON_ASSET"],
                            Session["AVALON_TASK"])

    menu = found_menu.menu()
    self._change_context_menu = label
    menu.setTitle(label)


def install():
    """
    Installing menu into Nukestudio

    """

    # here is the best place to add menu
    from avalon.tools import publish

    menu_name = os.environ['AVALON_LABEL']

    context_label = "{0}, {1}".format(
        Session["AVALON_ASSET"], Session["AVALON_TASK"]
    )

    self._change_context_menu = context_label

    # Grab Hiero's MenuBar
    M = hiero.ui.menuBar()

    try:
        check_made_menu = findMenuAction(menu_name)
    except Exception:
        pass

    if not check_made_menu:
        menu = M.addMenu(menu_name)
    else:
        menu = check_made_menu.menu()

    context_label_action = menu.addAction(context_label)
    context_label_action.setEnabled(False)

    menu.addSeparator()

    workfiles_action = menu.addAction("Work Files...")
    workfiles_action.setIcon("icons:Position.png")
    workfiles_action.triggered.connect(set_workfiles)

    default_tags_action = menu.addAction("Create Default Tags...")
    default_tags_action.setIcon("icons:Position.png")
    default_tags_action.triggered.connect(add_tags_from_presets)

    menu.addSeparator()

    publish_action = menu.addAction("Publish...")
    publish_action.setIcon("icons:Output.png")
    publish_action.triggered.connect(publish.show)

    menu.addSeparator()

    reload_action = menu.addAction("Reload pipeline...")
    reload_action.setIcon("icons:ColorAdd.png")
    reload_action.triggered.connect(reload_config)

    self.context_label_action = context_label_action
    self.workfile_actions = workfiles_action
    self.default_tags_action = default_tags_action
    self.publish_action = publish_action
    self.reload_action = reload_action
    # hiero.ui.registerAction(action)
