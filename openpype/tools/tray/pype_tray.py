import collections
import os
import sys
import atexit
import subprocess

import platform

from Qt import QtCore, QtGui, QtWidgets

import openpype.version
from openpype.api import (
    Logger,
    resources,
    get_system_settings
)
from openpype.lib import get_openpype_execute_args
from openpype.modules import TrayModulesManager
from openpype import style
from openpype.settings import (
    SystemSettings,
    ProjectSettings,
    DefaultsNotDefined
)
from openpype.tools.utils import WrappedCallbackItem

from .pype_info_widget import PypeInfoWidget


class TrayManager:
    """Cares about context of application.

    Load submenus, actions, separators and modules into tray's context.
    """

    def __init__(self, tray_widget, main_window):
        self.tray_widget = tray_widget
        self.main_window = main_window
        self.pype_info_widget = None

        self.log = Logger.get_logger(self.__class__.__name__)

        self.module_settings = get_system_settings()["modules"]

        self.modules_manager = TrayModulesManager()

        self.errors = []

        self.main_thread_timer = None
        self._main_thread_callbacks = collections.deque()
        self._execution_in_progress = None

    @property
    def doubleclick_callback(self):
        """Doubleclick callback for Tray icon."""
        callback_name = self.modules_manager.doubleclick_callback
        return self.modules_manager.doubleclick_callbacks.get(callback_name)

    def execute_doubleclick(self):
        """Execute double click callback in main thread."""
        callback = self.doubleclick_callback
        if callback:
            self.execute_in_main_thread(callback)

    def execute_in_main_thread(self, callback, *args, **kwargs):
        if isinstance(callback, WrappedCallbackItem):
            item = callback
        else:
            item = WrappedCallbackItem(callback, *args, **kwargs)

        self._main_thread_callbacks.append(item)

        return item

    def _main_thread_execution(self):
        if self._execution_in_progress:
            return
        self._execution_in_progress = True
        for _ in range(len(self._main_thread_callbacks)):
            if self._main_thread_callbacks:
                item = self._main_thread_callbacks.popleft()
                item.execute()

        self._execution_in_progress = False

    def initialize_modules(self):
        """Add modules to tray."""
        from openpype_interfaces import (
            ITrayAction,
            ITrayService
        )

        self.modules_manager.initialize(self, self.tray_widget.menu)

        admin_submenu = ITrayAction.admin_submenu(self.tray_widget.menu)
        self.tray_widget.menu.addMenu(admin_submenu)

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

        # create timer loop to check callback functions
        main_thread_timer = QtCore.QTimer()
        main_thread_timer.setInterval(300)
        main_thread_timer.timeout.connect(self._main_thread_execution)
        main_thread_timer.start()

        self.main_thread_timer = main_thread_timer

        # For storing missing settings dialog
        self._settings_validation_dialog = None

        self.execute_in_main_thread(self._startup_validations)

    def _startup_validations(self):
        """Run possible startup validations."""
        self._validate_settings_defaults()

    def _validate_settings_defaults(self):
        valid = True
        try:
            SystemSettings()
            ProjectSettings()

        except DefaultsNotDefined:
            valid = False

        if valid:
            return

        title = "Settings miss default values"
        msg = (
            "Your OpenPype will not work as expected! \n"
            "Some default values in settigs are missing. \n\n"
            "Please contact OpenPype team."
        )
        msg_box = QtWidgets.QMessageBox(
            QtWidgets.QMessageBox.Warning,
            title,
            msg,
            QtWidgets.QMessageBox.Ok,
            flags=QtCore.Qt.Dialog
        )
        icon = QtGui.QIcon(resources.get_openpype_icon_filepath())
        msg_box.setWindowIcon(icon)
        msg_box.setStyleSheet(style.load_stylesheet())
        msg_box.buttonClicked.connect(self._post_validate_settings_defaults)

        self._settings_validation_dialog = msg_box

        msg_box.show()

    def _post_validate_settings_defaults(self):
        widget = self._settings_validation_dialog
        self._settings_validation_dialog = None
        widget.deleteLater()

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
        subversion = os.environ.get("OPENPYPE_SUBVERSION")
        client_name = os.environ.get("OPENPYPE_CLIENT")

        version_string = openpype.version.__version__
        if subversion:
            version_string += " ({})".format(subversion)

        if client_name:
            version_string += ", {}".format(client_name)

        version_action = QtWidgets.QAction(version_string, self.tray_widget)
        version_action.triggered.connect(self._on_version_action)
        self.tray_widget.menu.addAction(version_action)
        self.tray_widget.menu.addSeparator()

    def restart(self):
        """Restart Tray tool.

        First creates new process with same argument and close current tray.
        """
        args = get_openpype_execute_args()
        # Create a copy of sys.argv
        additional_args = list(sys.argv)
        # Check last argument from `get_openpype_execute_args`
        # - when running from code it is the same as first from sys.argv
        if args[-1] == additional_args[0]:
            additional_args.pop(0)
        args.extend(additional_args)

        kwargs = {}
        if platform.system().lower() == "windows":
            flags = (
                subprocess.CREATE_NEW_PROCESS_GROUP
                | subprocess.DETACHED_PROCESS
            )
            kwargs["creationflags"] = flags

        subprocess.Popen(args, **kwargs)
        self.exit()

    def exit(self):
        self.tray_widget.exit()

    def on_exit(self):
        self.modules_manager.on_exit()

    def _on_version_action(self):
        if self.pype_info_widget is None:
            self.pype_info_widget = PypeInfoWidget()

        self.pype_info_widget.show()
        self.pype_info_widget.raise_()
        self.pype_info_widget.activateWindow()


class SystemTrayIcon(QtWidgets.QSystemTrayIcon):
    """Tray widget.

    :param parent: Main widget that cares about all GUIs
    :type parent: QtWidgets.QMainWindow
    """

    doubleclick_time_ms = 100

    def __init__(self, parent):
        icon = QtGui.QIcon(resources.get_openpype_icon_filepath())

        super(SystemTrayIcon, self).__init__(icon, parent)

        self._exited = False

        # Store parent - QtWidgets.QMainWindow()
        self.parent = parent

        # Setup menu in Tray
        self.menu = QtWidgets.QMenu()
        self.menu.setStyleSheet(style.load_stylesheet())

        # Set modules
        self.tray_man = TrayManager(self, self.parent)

        # Add menu to Context of SystemTrayIcon
        self.setContextMenu(self.menu)

        atexit.register(self.exit)

        # Catch activate event for left click if not on MacOS
        #   - MacOS has this ability by design and is harder to modify this
        #       behavior
        if platform.system().lower() == "darwin":
            return

        self.activated.connect(self.on_systray_activated)

        click_timer = QtCore.QTimer()
        click_timer.setInterval(self.doubleclick_time_ms)
        click_timer.timeout.connect(self._click_timer_timeout)

        self._click_timer = click_timer
        self._doubleclick = False
        self._click_pos = None

        self._initializing_modules = False

    @property
    def initializing_modules(self):
        return self._initializing_modules

    def initialize_modules(self):
        self._initializing_modules = True
        self.tray_man.initialize_modules()
        self._initializing_modules = False

    def _click_timer_timeout(self):
        self._click_timer.stop()
        doubleclick = self._doubleclick
        # Reset bool value
        self._doubleclick = False
        if doubleclick:
            self.tray_man.execute_doubleclick()
        else:
            self._show_context_menu()

    def _show_context_menu(self):
        pos = self._click_pos
        self._click_pos = None
        if pos is None:
            pos = QtGui.QCursor().pos()
        self.contextMenu().popup(pos)

    def on_systray_activated(self, reason):
        # show contextMenu if left click
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            if self.tray_man.doubleclick_callback:
                self._click_pos = QtGui.QCursor().pos()
                self._click_timer.start()
            else:
                self._show_context_menu()

        elif reason == QtWidgets.QSystemTrayIcon.DoubleClick:
            self._doubleclick = True

    def exit(self):
        """ Exit whole application.

        - Icon won't stay in tray after exit.
        """
        if self._exited:
            return
        self._exited = True

        self.hide()
        self.tray_man.on_exit()
        QtCore.QCoreApplication.exit()


class PypeTrayStarter(QtCore.QObject):
    def __init__(self, app):
        app.setQuitOnLastWindowClosed(False)
        self._app = app
        self._splash = None

        main_window = QtWidgets.QMainWindow()
        tray_widget = SystemTrayIcon(main_window)

        start_timer = QtCore.QTimer()
        start_timer.setInterval(100)
        start_timer.start()

        start_timer.timeout.connect(self._on_start_timer)

        self._main_window = main_window
        self._tray_widget = tray_widget
        self._timer_counter = 0
        self._start_timer = start_timer

    def _on_start_timer(self):
        if self._timer_counter == 0:
            self._timer_counter += 1
            splash = self._get_splash()
            splash.show()
            self._tray_widget.show()
            # Make sure tray and splash are painted out
            QtWidgets.QApplication.processEvents()

        elif self._timer_counter == 1:
            # Second processing of events to make sure splash is painted
            QtWidgets.QApplication.processEvents()
            self._timer_counter += 1
            self._tray_widget.initialize_modules()

        elif not self._tray_widget.initializing_modules:
            splash = self._get_splash()
            splash.hide()
            self._start_timer.stop()

    def _get_splash(self):
        if self._splash is None:
            self._splash = self._create_splash()
        return self._splash

    def _create_splash(self):
        splash_pix = QtGui.QPixmap(resources.get_openpype_splash_filepath())
        splash = QtWidgets.QSplashScreen(splash_pix)
        splash.setMask(splash_pix.mask())
        splash.setEnabled(False)
        splash.setWindowFlags(
            QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.FramelessWindowHint
        )
        return splash


def main():
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication([])

    starter = PypeTrayStarter(app)

    # TODO remove when pype.exe will have an icon
    if os.name == "nt":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            u"pype_tray"
        )

    sys.exit(app.exec_())
