import sys
import os
from Qt import QtCore
from Qt import QtWidgets
from openpype import style
from openpype.settings import get_project_settings
from openpype.tools.utils import lib as tools_lib

import scriptsmenu
import logging

log = logging.getLogger(__name__)
module = sys.modules[__name__]
module.window = None


class StudioToolsDialog(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(StudioToolsDialog, self).__init__(parent)

        self.resize(400, 300)
        self.setStyleSheet(style.load_stylesheet())

        project_settings = get_project_settings(os.getenv("AVALON_PROJECT"))
        host = os.getenv("AVALON_APP")
        config = project_settings[host]["scriptsmenu"]["definition"]
        _menu = project_settings[host]["scriptsmenu"]["name"]
        self.setWindowTitle(_menu)

        title = _menu.title()
        objectName = _menu.title().lower().replace(" ", "_")

        layout = QtWidgets.QVBoxLayout()

        try:
            log.info("Attempting to build menu ...")
            object_name = objectName or title.lower()
            menu = scriptsmenu.ScriptsMenu(title=title,
                                           parent=parent,
                                           objectName=object_name)
            layout.addWidget(menu)
            menu.aboutToHide.connect(menu.show)  # IF menu try to hide -> Don't
        except Exception as e:
            log.error(e)
            return
        finally:
            self.setLayout(layout)

        # apply configuration
        self.layout = layout
        menu.build_from_configuration(menu, config)
        self.menu = menu


def show(debug=False, parent=None):
    """Display Loader GUI

    Arguments:
        debug (bool, optional): Run loader in debug-mode,
            defaults to False
        parent (QtCore.QObject, optional): The Qt object to parent to.
        use_context (bool): Whether to apply the current context upon launch

    """
    # Remember window
    if module.window is not None:
        try:
            module.window.show()

            # If the window is minimized then unminimize it.
            if module.window.windowState() & QtCore.Qt.WindowMinimized:
                module.window.setWindowState(QtCore.Qt.WindowActive)

            # Raise and activate the window
            module.window.raise_()             # for MacOS
            module.window.activateWindow()     # for Windows
            module.window.refresh()
            return
        except RuntimeError as e:
            if not e.message.rstrip().endswith("already deleted."):
                raise

            # Garbage collected
            module.window = None

    if debug:
        import traceback
        sys.excepthook = lambda typ, val, tb: traceback.print_last()

    with tools_lib.qt_app_context():
        window = StudioToolsDialog(parent)
        window.show()

        module.window = window
