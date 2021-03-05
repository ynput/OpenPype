import os
import sys

import platform
from avalon import style
from Qt import QtCore, QtGui, QtWidgets, QtSvg
from pype.api import Logger, resources
from pype.modules import TrayModulesManager, ITrayService
from pype.settings.lib import get_system_settings
import pype.version


class TrayManager:
    """Cares about context of application.

    Load submenus, actions, separators and modules into tray's context.
    """
    available_sourcetypes = ["python", "file"]

    def __init__(self, tray_widget, main_window):
        self.tray_widget = tray_widget
        self.main_window = main_window

        self.log = Logger().get_logger(self.__class__.__name__)

        self.module_settings = get_system_settings()["modules"]

        self.modules_manager = TrayModulesManager()

        self.errors = []

    def initialize_modules(self):
        """Add modules to tray."""

        self.modules_manager.initialize(self.tray_widget.menu)

        # Add services if they are
        services_submenu = ITrayService.services_submenu(self.tray_widget.menu)
        self.tray_widget.menu.addMenu(services_submenu)

        # Add separator
        self.tray_widget.menu.addSeparator()

        self._add_version_item()

        # Add Exit action to menu
        exit_action = QtWidgets.QAction("Exit", self.tray_widget)
        exit_action.triggered.connect(self.tray_widget.exit)
        self.tray_widget.menu.addAction(exit_action)

        # Tell each module which modules were imported
        self.modules_manager.start_modules()

        # Print time report
        self.modules_manager.print_report()

    def _add_version_item(self):
        subversion = os.environ.get("PYPE_SUBVERSION")
        client_name = os.environ.get("PYPE_CLIENT")

        version_string = pype.version.__version__
        if subversion:
            version_string += " ({})".format(subversion)

        if client_name:
            version_string += ", {}".format(client_name)

        version_action = QtWidgets.QAction(version_string, self.tray_widget)
        self.tray_widget.menu.addAction(version_action)
        self.tray_widget.menu.addSeparator()

    def on_exit(self):
        self.modules_manager.on_exit()


class SystemTrayIcon(QtWidgets.QSystemTrayIcon):
    """Tray widget.

    :param parent: Main widget that cares about all GUIs
    :type parent: QtWidgets.QMainWindow
    """

    def __init__(self, parent):
        self.icon = QtGui.QIcon(resources.pype_icon_filepath())

        QtWidgets.QSystemTrayIcon.__init__(self, self.icon, parent)

        # Store parent - QtWidgets.QMainWindow()
        self.parent = parent

        # Setup menu in Tray
        self.menu = QtWidgets.QMenu()
        self.menu.setStyleSheet(style.load_stylesheet())

        # Set modules
        self.tray_man = TrayManager(self, self.parent)
        self.tray_man.initialize_modules()

        # Catch activate event
        self.activated.connect(self.on_systray_activated)
        # Add menu to Context of SystemTrayIcon
        self.setContextMenu(self.menu)

    def on_systray_activated(self, reason):
        # show contextMenu if left click
        if platform.system().lower() == "darwin":
            return
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            position = QtGui.QCursor().pos()
            self.contextMenu().popup(position)

    def exit(self):
        """ Exit whole application.

        - Icon won't stay in tray after exit.
        """
        self.hide()
        self.tray_man.on_exit()
        QtCore.QCoreApplication.exit()


class TrayMainWindow(QtWidgets.QMainWindow):
    """ TrayMainWindow is base of Pype application.

    Every widget should have set this window as parent because
    QSystemTrayIcon widget is not allowed to be a parent of any widget.

    :param app: Qt application manages application's control flow
    :type app: QtWidgets.QApplication

    .. note::
        *TrayMainWindow* has ability to show **working** widget.
        Calling methods:
        - ``show_working()``
        - ``hide_working()``
    .. todo:: Hide working widget if idle is too long
    """

    def __init__(self, app):
        super().__init__()
        self.app = app

        self.set_working_widget()

        self.trayIcon = SystemTrayIcon(self)
        self.trayIcon.show()

    def set_working_widget(self):
        image_file = resources.get_resource("icons", "working.svg")
        img_pix = QtGui.QPixmap(image_file)
        if image_file.endswith('.svg'):
            widget = QtSvg.QSvgWidget(image_file)
        else:
            widget = QtWidgets.QLabel()
            widget.setPixmap(img_pix)

        # Set widget properties
        widget.setGeometry(img_pix.rect())
        widget.setMask(img_pix.mask())
        widget.setWindowFlags(
            QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.FramelessWindowHint
        )
        widget.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        self.center_widget(widget)
        self._working_widget = widget
        self.helper = DragAndDropHelper(self._working_widget)

    def center_widget(self, widget):
        frame_geo = widget.frameGeometry()
        screen = self.app.desktop().cursor().pos()
        center_point = self.app.desktop().screenGeometry(
            self.app.desktop().screenNumber(screen)
        ).center()
        frame_geo.moveCenter(center_point)
        widget.move(frame_geo.topLeft())

    def show_working(self):
        self._working_widget.show()

    def hide_working(self):
        self.center_widget(self._working_widget)
        self._working_widget.hide()


class DragAndDropHelper:
    """ Helper adds to widget drag and drop ability

    :param widget: Qt Widget where drag and drop ability will be added
    """

    def __init__(self, widget):
        self.widget = widget
        self.widget.mousePressEvent = self.mousePressEvent
        self.widget.mouseMoveEvent = self.mouseMoveEvent
        self.widget.mouseReleaseEvent = self.mouseReleaseEvent

    def mousePressEvent(self, event):
        self.__mousePressPos = None
        self.__mouseMovePos = None
        if event.button() == QtCore.Qt.LeftButton:
            self.__mousePressPos = event.globalPos()
            self.__mouseMovePos = event.globalPos()

    def mouseMoveEvent(self, event):
        if event.buttons() == QtCore.Qt.LeftButton:
            # adjust offset from clicked point to origin of widget
            currPos = self.widget.mapToGlobal(
                self.widget.pos()
            )
            globalPos = event.globalPos()
            diff = globalPos - self.__mouseMovePos
            newPos = self.widget.mapFromGlobal(currPos + diff)
            self.widget.move(newPos)
            self.__mouseMovePos = globalPos

    def mouseReleaseEvent(self, event):
        if self.__mousePressPos is not None:
            moved = event.globalPos() - self.__mousePressPos
            if moved.manhattanLength() > 3:
                event.ignore()
                return


class PypeTrayApplication(QtWidgets.QApplication):
    """Qt application manages application's control flow."""

    def __init__(self):
        super(self.__class__, self).__init__(sys.argv)
        # Allows to close widgets without exiting app
        self.setQuitOnLastWindowClosed(False)

        # Allow show icon istead of python icon in task bar (Windows)
        if os.name == "nt":
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                u"pype_tray"
            )

        # Sets up splash
        splash_widget = self.set_splash()

        splash_widget.show()
        self.processEvents()
        self.main_window = TrayMainWindow(self)
        splash_widget.hide()

    def set_splash(self):
        splash_pix = QtGui.QPixmap(resources.pype_splash_filepath())
        splash = QtWidgets.QSplashScreen(splash_pix)
        splash.setMask(splash_pix.mask())
        splash.setEnabled(False)
        splash.setWindowFlags(
            QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.FramelessWindowHint
        )
        return splash


def main():
    app = PypeTrayApplication()
    # TODO remove when pype.exe will have an icon
    if os.name == "nt":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            u"pype_tray"
        )

    sys.exit(app.exec_())
