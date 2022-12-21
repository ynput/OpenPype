
# Import third-party modules
from qtpy import QtWidgets

# Import local modules
import scriptsmenu


def _mari_main_window():
    """Get Mari main window.

    Returns:
        MriMainWindow: Mari's main window.

    """
    for obj in QtWidgets.QApplication.topLevelWidgets():
        if obj.metaObject().className() == 'MriMainWindow':
            return obj
    raise RuntimeError('Could not find Mari MainWindow instance')


def _mari_main_menubar():
    """Get Mari main menu bar.

    Returns:
        Retrieve the main menubar of the Mari window.

    """
    mari_window = _mari_main_window()
    menubar = [
        i for i in mari_window.children() if isinstance(i, QtWidgets.QMenuBar)
    ]
    assert len(menubar) == 1, "Error, could not find menu bar!"
    return menubar[0]


def main(title="Scripts"):
    """Build the main scripts menu in Mari.

    Args:
        title (str): Name of the menu in the application.

    Returns:
        scriptsmenu.ScriptsMenu:  Instance object.

    """
    mari_main_bar = _mari_main_menubar()
    for mari_bar in mari_main_bar.children():
        if isinstance(mari_bar, scriptsmenu.ScriptsMenu):
            if mari_bar.title() == title:
                menu = mari_bar
                return menu
    menu = scriptsmenu.ScriptsMenu(title=title, parent=mari_main_bar)
    return menu
