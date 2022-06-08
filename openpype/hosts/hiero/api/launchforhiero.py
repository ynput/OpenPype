import logging

from openpype.vendor.python.common.scriptsmenu import scriptsmenu
from openpype.vendor.python.common.scriptsmenu.vendor.Qt import QtWidgets


log = logging.getLogger(__name__)


def _hiero_main_window():
    """Return Hiero's main window"""
    for obj in QtWidgets.QApplication.topLevelWidgets():
        if (obj.inherits('QMainWindow') and
                obj.metaObject().className() == 'Foundry::UI::DockMainWindow'):
            return obj
    raise RuntimeError('Could not find HieroWindow instance')


def _hiero_main_menubar():
    """Retrieve the main menubar of the Hiero window"""
    hiero_window = _hiero_main_window()
    menubar = [i for i in hiero_window.children() if isinstance(
        i,
        QtWidgets.QMenuBar
    )]

    assert len(menubar) == 1, "Error, could not find menu bar!"
    return menubar[0]


def find_scripts_menu(title, parent):
    """
    Check if the menu exists with the given title in the parent

    Args:
        title (str): the title name of the scripts menu

        parent (QtWidgets.QMenuBar): the menubar to check

    Returns:
        QtWidgets.QMenu or None

    """

    menu = None
    search = [i for i in parent.children() if
              isinstance(i, scriptsmenu.ScriptsMenu)
              and i.title() == title]
    if search:
        assert len(search) < 2, ("Multiple instances of menu '{}' "
                                 "in menu bar".format(title))
        menu = search[0]

    return menu


def main(title="Scripts", parent=None, objectName=None):
    """Build the main scripts menu in Hiero

    Args:
        title (str): name of the menu in the application

        parent (QtWidgets.QtMenuBar): the parent object for the menu

        objectName (str): custom objectName for scripts menu

    Returns:
        scriptsmenu.ScriptsMenu instance

    """
    hieromainbar = parent or _hiero_main_menubar()
    try:
        # check menu already exists
        menu = find_scripts_menu(title, hieromainbar)
        if not menu:
            log.info("Attempting to build menu ...")
            object_name = objectName or title.lower()
            menu = scriptsmenu.ScriptsMenu(title=title,
                                           parent=hieromainbar,
                                           objectName=object_name)
    except Exception as e:
        log.error(e)
        return

    return menu
