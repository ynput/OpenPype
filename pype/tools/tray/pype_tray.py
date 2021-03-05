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

    def __init__(self, tray_widget, main_window):
        self.tray_widget = tray_widget
        self.main_window = main_window

        self.log = Logger.get_logger(self.__class__.__name__)

        self.module_settings = get_system_settings()["modules"]

        self.modules_manager = TrayModulesManager()

        self.errors = []

    def initialize_modules(self):
        """Add modules to tray."""

        self.modules_manager.initialize(self, self.tray_widget.menu)

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

    def show_tray_message(self, title, message, icon=None, msecs=None):
        """Show tray message.

        Args:
            title (str): Title of message.
            message (str): Content of message.
            icon (QSystemTrayIcon.MessageIcon): Message's icon. Default is
                Information icon, may differ by Qt version.
            msecs (int): Duration of message visibility in miliseconds.
                Default is 10000 msecs, may differ by Qt version.
        """
        args = [title, message]
        kwargs = {}
        if icon:
            kwargs["icon"] = icon
        if msecs:
            kwargs["msecs"] = msecs

        self.tray_widget.showMessage(*args, **kwargs)

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
        icon = QtGui.QIcon(resources.pype_icon_filepath())

        super(SystemTrayIcon, self).__init__(icon, parent)

        # Store parent - QtWidgets.QMainWindow()
        self.parent = parent

        # Setup menu in Tray
        self.menu = QtWidgets.QMenu()
        self.menu.setStyleSheet(style.load_stylesheet())

        # Set modules
        self.tray_man = TrayManager(self, self.parent)
        self.tray_man.initialize_modules()

        # Catch activate event for left click if not on MacOS
        #   - MacOS has this ability by design so menu would be doubled
        if platform.system().lower() != "darwin":
            self.activated.connect(self.on_systray_activated)
        # Add menu to Context of SystemTrayIcon
        self.setContextMenu(self.menu)

    def on_systray_activated(self, reason):
        # show contextMenu if left click
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
    """

    def __init__(self, app):
        super(TrayMainWindow, self).__init__()
        self.app = app

        self.tray_widget = SystemTrayIcon(self)
        self.tray_widget.show()


class PypeTrayApplication(QtWidgets.QApplication):
    """Qt application manages application's control flow."""

    def __init__(self):
        super(PypeTrayApplication, self).__init__(sys.argv)
        # Allows to close widgets without exiting app
        self.setQuitOnLastWindowClosed(False)

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
