from avalon.api import Session

from pype.nukestudio import lib


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
    except:
        pass

    if not check_made_menu:
        menu = M.addMenu(menu_name)
    else:
        menu = check_made_menu.menu()

    actions = [{
        'action': QAction(QIcon('icons:Position.png'), 'Set Context', None),
        'function': contextmanager.show
    },
        {
        'action': QAction(QIcon('icons:ColorAdd.png'), 'Create...', None),
        'function': creator.show
    },
        {
        'action': QAction(QIcon('icons:CopyRectangle.png'), 'Load...', None),
        'function': cbloader.show
    },
        {
        'action': QAction(QIcon('icons:Output.png'), 'Publish...', None),
        'function': publish.show
    },
        {
        'action': QAction(QIcon('icons:ModifyMetaData.png'), 'Manage...', None),
        'function': cbsceneinventory.show
    },
        {
        'action': QAction(QIcon('icons:ColorAdd.png'), 'Library...', None),
        'function': libraryloader.show
    }]


    # Create menu items
    for a in actions:
        # create action
        for k in a.keys():
            if 'action' in k:
                action = a[k]
            elif 'function' in k:
                action.triggered.connect(a[k])
            else:
                pass
        # add action to menu
        menu.addAction(action)
