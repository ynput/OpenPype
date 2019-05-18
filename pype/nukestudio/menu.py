import os
from avalon.api import Session
from pprint import pprint

import hiero.core

try:
    from PySide.QtGui import *
except Exception:
    from PySide2.QtGui import *
    from PySide2.QtWidgets import *

from hiero.ui import findMenuAction


#
def install():
    # here is the best place to add menu
    from avalon.tools import (
        creator,
        publish,
        workfiles,
        cbloader,
        cbsceneinventory,
        contextmanager,
        libraryloader
    )

    menu_name = os.environ['PYPE_STUDIO_NAME']
    # Grab Hiero's MenuBar
    M = hiero.ui.menuBar()

    # Add a Menu to the MenuBar
    file_action = None

    try:
        check_made_menu = findMenuAction(menu_name)
    except Exception:
        pass

    if not check_made_menu:
        menu = M.addMenu(menu_name)
    else:
        menu = check_made_menu.menu()

    actions = [{
        'action': QAction('Set Context', None),
        'function': contextmanager.show,
        'icon': QIcon('icons:Position.png')
    },
        {
        'action': QAction('Create...', None),
        'function': creator.show,
        'icon': QIcon('icons:ColorAdd.png')
    },
        {
        'action': QAction('Load...', None),
        'function': cbloader.show,
        'icon': QIcon('icons:CopyRectangle.png')
    },
        {
        'action': QAction('Publish...', None),
        'function': publish.show,
        'icon': QIcon('icons:Output.png')
    },
        {
        'action': QAction('Manage...', None),
        'function': cbsceneinventory.show,
        'icon': QIcon('icons:ModifyMetaData.png')
    },
        {
        'action': QAction('Library...', None),
        'function': libraryloader.show,
        'icon': QIcon('icons:ColorAdd.png')
    }]


    # Create menu items
    for a in actions:
        pprint(a)
        # create action
        for k in a.keys():
            if 'action' in k:
                action = a[k]
            elif 'function' in k:
                action.triggered.connect(a[k])
            elif 'icon' in k:
                action.setIcon(a[k])

        # add action to menu
        menu.addAction(action)
        hiero.ui.registerAction(action)
