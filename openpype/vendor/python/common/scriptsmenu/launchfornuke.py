import scriptsmenu
from .vendor.Qt import QtWidgets


def _nuke_main_window():
    """Return Nuke's main window"""
    for obj in QtWidgets.QApplication.topLevelWidgets():
        if (obj.inherits('QMainWindow') and
                    obj.metaObject().className() == 'Foundry::UI::DockMainWindow'):
            return obj
    raise RuntimeError('Could not find Nuke MainWindow instance')


def _nuke_main_menubar():
    """Retrieve the main menubar of the Nuke window"""
    nuke_window = _nuke_main_window()
    menubar = [i for i in nuke_window.children()
               if isinstance(i, QtWidgets.QMenuBar)]

    assert len(menubar) == 1, "Error, could not find menu bar!"
    return menubar[0]


def main(title="Scripts"):
    nuke_main_bar = _nuke_main_menubar()
    for nuke_bar in nuke_main_bar.children():
        if isinstance(nuke_bar, scriptsmenu.ScriptsMenu):
            if nuke_bar.title() == title:
                menu = nuke_bar
                return menu

    menu = scriptsmenu.ScriptsMenu(title=title, parent=nuke_main_bar)
    return menu
