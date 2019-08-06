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
    from avalon.tools import (
        creator,
        publish,
        cbloader,
        cbsceneinventory,
        contextmanager,
        libraryloader
    )

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

    actions = [
        {
            'parent': context_label,
            'action': QAction('Set Context', None),
            'function': contextmanager.show,
            'icon': QIcon('icons:Position.png')
        },
        "separator",
        {
            'action': QAction("Work Files...", None),
            'function': set_workfiles,
            'icon': QIcon('icons:Position.png')
        },
        {
            'action': QAction('Create Default Tags..', None),
            'function': add_tags_from_presets,
            'icon': QIcon('icons:Position.png')
        },
        "separator",
        # {
        #     'action': QAction('Create...', None),
        #     'function': creator.show,
        #     'icon': QIcon('icons:ColorAdd.png')
        # },
        # {
        #     'action': QAction('Load...', None),
        #     'function': cbloader.show,
        #     'icon': QIcon('icons:CopyRectangle.png')
        # },
        {
            'action': QAction('Publish...', None),
            'function': publish.show,
            'icon': QIcon('icons:Output.png')
        },
        # {
        #     'action': QAction('Manage...', None),
        #     'function': cbsceneinventory.show,
        #     'icon': QIcon('icons:ModifyMetaData.png')
        # },
        {
            'action': QAction('Library...', None),
            'function': libraryloader.show,
            'icon': QIcon('icons:ColorAdd.png')
        },
        "separator",
        {
            'action': QAction('Reload pipeline...', None),
            'function': reload_config,
            'icon': QIcon('icons:ColorAdd.png')
        }]

    # Create menu items
    for a in actions:
        add_to_menu = menu
        if isinstance(a, dict):
            # create action
            for k in a.keys():
                if 'parent' in k:
                    submenus = [sm for sm in a[k].split('/')]
                    submenu = None
                    for sm in submenus:
                        if submenu:
                            submenu.addMenu(sm)
                        else:
                            submenu = menu.addMenu(sm)
                    add_to_menu = submenu
                if 'action' in k:
                    action = a[k]
                elif 'function' in k:
                    action.triggered.connect(a[k])
                elif 'icon' in k:
                    action.setIcon(a[k])

            # add action to menu
            add_to_menu.addAction(action)
            hiero.ui.registerAction(action)
        elif isinstance(a, str):
            add_to_menu.addSeparator()
