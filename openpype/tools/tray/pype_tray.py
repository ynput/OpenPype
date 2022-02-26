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
from openpype.lib import (
    get_openpype_execute_args,
    op_version_control_available,
    is_current_version_studio_latest,
    is_current_version_higher_than_expected,
    is_running_from_build,
    is_running_staging,
    get_expected_version,
    get_openpype_version
)
from openpype.modules import TrayModulesManager
from openpype import style
from openpype.settings import (
    SystemSettings,
    ProjectSettings,
    DefaultsNotDefined
)
from openpype.tools.utils import (
    WrappedCallbackItem,
    paint_image_with_color,
    get_warning_pixmap
)

from .pype_info_widget import PypeInfoWidget


# TODO PixmapLabel should be moved to 'utils' in other future PR so should be
#   imported from there
class PixmapLabel(QtWidgets.QLabel):
    """Label resizing image to height of font."""
    def __init__(self, pixmap, parent):
        super(PixmapLabel, self).__init__(parent)
        self._empty_pixmap = QtGui.QPixmap(0, 0)
        self._source_pixmap = pixmap

    def set_source_pixmap(self, pixmap):
        """Change source image."""
        self._source_pixmap = pixmap
        self._set_resized_pix()

    def _get_pix_size(self):
        size = self.fontMetrics().height() * 3
        return size, size

    def _set_resized_pix(self):
        if self._source_pixmap is None:
            self.setPixmap(self._empty_pixmap)
            return
        width, height = self._get_pix_size()
        self.setPixmap(
            self._source_pixmap.scaled(
                width,
                height,
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )
        )

    def resizeEvent(self, event):
        self._set_resized_pix()
        super(PixmapLabel, self).resizeEvent(event)


class VersionUpdateDialog(QtWidgets.QDialog):
    restart_requested = QtCore.Signal()
    ignore_requested = QtCore.Signal()

    _min_width = 400
    _min_height = 130

    def __init__(self, parent=None):
        super(VersionUpdateDialog, self).__init__(parent)

        icon = QtGui.QIcon(resources.get_openpype_icon_filepath())
        self.setWindowIcon(icon)
        self.setWindowFlags(
            self.windowFlags()
            | QtCore.Qt.WindowStaysOnTopHint
        )

        self.setMinimumWidth(self._min_width)
        self.setMinimumHeight(self._min_height)

        top_widget = QtWidgets.QWidget(self)

        gift_pixmap = self._get_gift_pixmap()
        gift_icon_label = PixmapLabel(gift_pixmap, top_widget)

        label_widget = QtWidgets.QLabel(top_widget)
        label_widget.setWordWrap(True)

        top_layout = QtWidgets.QHBoxLayout(top_widget)
        top_layout.setSpacing(10)
        top_layout.addWidget(gift_icon_label, 0, QtCore.Qt.AlignCenter)
        top_layout.addWidget(label_widget, 1)

        ignore_btn = QtWidgets.QPushButton(self)
        restart_btn = QtWidgets.QPushButton(self)
        restart_btn.setObjectName("TrayRestartButton")

        btns_layout = QtWidgets.QHBoxLayout()
        btns_layout.addStretch(1)
        btns_layout.addWidget(ignore_btn, 0)
        btns_layout.addWidget(restart_btn, 0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(top_widget, 0)
        layout.addStretch(1)
        layout.addLayout(btns_layout, 0)

        ignore_btn.clicked.connect(self._on_ignore)
        restart_btn.clicked.connect(self._on_reset)

        self._label_widget = label_widget
        self._gift_icon_label = gift_icon_label
        self._ignore_btn = ignore_btn
        self._restart_btn = restart_btn

        self._restart_accepted = False
        self._current_is_higher = False

        self.setStyleSheet(style.load_stylesheet())

    def _get_gift_pixmap(self):
        image_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "images",
            "gifts.png"
        )
        src_image = QtGui.QImage(image_path)
        colors = style.get_objected_colors()
        color_value = colors["font"]

        return paint_image_with_color(
            src_image,
            color_value.get_qcolor()
        )

    def showEvent(self, event):
        super(VersionUpdateDialog, self).showEvent(event)
        self._restart_accepted = False

    def closeEvent(self, event):
        super(VersionUpdateDialog, self).closeEvent(event)
        if self._restart_accepted or self._current_is_higher:
            return
        # Trigger ignore requested only if restart was not clicked and current
        #   version is lower
        self.ignore_requested.emit()

    def update_versions(
        self, current_version, expected_version, current_is_higher
    ):
        if not current_is_higher:
            title = "OpenPype update is needed"
            label_message = (
                "Running OpenPype version is <b>{}</b>."
                " Your production has been updated to version <b>{}</b>."
            ).format(str(current_version), str(expected_version))
            ignore_label = "Later"
            restart_label = "Restart && Update"
        else:
            title = "OpenPype version is higher"
            label_message = (
                "Running OpenPype version is <b>{}</b>."
                " Your production uses version <b>{}</b>."
            ).format(str(current_version), str(expected_version))
            ignore_label = "Ignore"
            restart_label = "Restart && Change"

        self.setWindowTitle(title)

        self._current_is_higher = current_is_higher

        self._gift_icon_label.setVisible(not current_is_higher)

        self._label_widget.setText(label_message)
        self._ignore_btn.setText(ignore_label)
        self._restart_btn.setText(restart_label)

    def _on_ignore(self):
        self.reject()

    def _on_reset(self):
        self._restart_accepted = True
        self.restart_requested.emit()
        self.accept()


class BuildVersionDialog(QtWidgets.QDialog):
    """Build/Installation version is too low for current OpenPype version.

    This dialog tells to user that it's build OpenPype is too old.
    """
    def __init__(self, parent=None):
        super(BuildVersionDialog, self).__init__(parent)

        icon = QtGui.QIcon(resources.get_openpype_icon_filepath())
        self.setWindowIcon(icon)
        self.setWindowTitle("Outdated OpenPype installation")
        self.setWindowFlags(
            self.windowFlags()
            | QtCore.Qt.WindowStaysOnTopHint
        )

        top_widget = QtWidgets.QWidget(self)

        warning_pixmap = get_warning_pixmap()
        warning_icon_label = PixmapLabel(warning_pixmap, top_widget)

        message = (
            "Your installation of OpenPype <b>does not match minimum"
            " requirements</b>.<br/><br/>Please update OpenPype installation"
            " to newer version."
        )
        content_label = QtWidgets.QLabel(message, self)

        top_layout = QtWidgets.QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(
            warning_icon_label, 0,
            QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter
        )
        top_layout.addWidget(content_label, 1)

        footer_widget = QtWidgets.QWidget(self)
        ok_btn = QtWidgets.QPushButton("I understand", footer_widget)

        footer_layout = QtWidgets.QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.addStretch(1)
        footer_layout.addWidget(ok_btn)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(top_widget, 0)
        main_layout.addStretch(1)
        main_layout.addWidget(footer_widget, 0)

        self.setStyleSheet(style.load_stylesheet())

        ok_btn.clicked.connect(self._on_ok_clicked)

    def _on_ok_clicked(self):
        self.close()


class TrayManager:
    """Cares about context of application.

    Load submenus, actions, separators and modules into tray's context.
    """
    def __init__(self, tray_widget, main_window):
        self.tray_widget = tray_widget
        self.main_window = main_window
        self.pype_info_widget = None
        self._restart_action = None

        self.log = Logger.get_logger(self.__class__.__name__)

        system_settings = get_system_settings()
        self.module_settings = system_settings["modules"]

        version_check_interval = system_settings["general"].get(
            "version_check_interval"
        )
        if version_check_interval is None:
            version_check_interval = 5
        self._version_check_interval = version_check_interval * 60 * 1000

        self.modules_manager = TrayModulesManager()

        self.errors = []

        self._version_check_timer = None
        self._version_dialog = None

        self.main_thread_timer = None
        self._main_thread_callbacks = collections.deque()
        self._execution_in_progress = None

    @property
    def doubleclick_callback(self):
        """Double-click callback for Tray icon."""
        callback_name = self.modules_manager.doubleclick_callback
        return self.modules_manager.doubleclick_callbacks.get(callback_name)

    def execute_doubleclick(self):
        """Execute double click callback in main thread."""
        callback = self.doubleclick_callback
        if callback:
            self.execute_in_main_thread(callback)

    def _on_version_check_timer(self):
        # Check if is running from build and stop future validations if yes
        if not is_running_from_build() or not op_version_control_available():
            self._version_check_timer.stop()
            return

        self.validate_openpype_version()

    def validate_openpype_version(self):
        using_requested = is_current_version_studio_latest()
        # TODO Handle situations when version can't be detected
        if using_requested is None:
            using_requested = True

        self._restart_action.setVisible(not using_requested)
        if using_requested:
            if (
                self._version_dialog is not None
                and self._version_dialog.isVisible()
            ):
                self._version_dialog.close()
            return

        if self._version_dialog is None:
            self._version_dialog = VersionUpdateDialog()
            self._version_dialog.restart_requested.connect(
                self._restart_and_install
            )
            self._version_dialog.ignore_requested.connect(
                self._outdated_version_ignored
            )

        expected_version = get_expected_version()
        current_version = get_openpype_version()
        current_is_higher = is_current_version_higher_than_expected()

        self._version_dialog.update_versions(
            current_version, expected_version, current_is_higher
        )
        self._version_dialog.show()
        self._version_dialog.raise_()
        self._version_dialog.activateWindow()

    def _restart_and_install(self):
        self.restart(use_expected_version=True)

    def _outdated_version_ignored(self):
        self.show_tray_message(
            "OpenPype version is outdated",
            (
                "Please update your OpenPype as soon as possible."
                " To update, restart OpenPype Tray application."
            )
        )

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

        version_check_timer = QtCore.QTimer()
        if self._version_check_interval > 0:
            version_check_timer.timeout.connect(self._on_version_check_timer)
            version_check_timer.setInterval(self._version_check_interval)
            version_check_timer.start()
        self._version_check_timer = version_check_timer

        # For storing missing settings dialog
        self._settings_validation_dialog = None

        self.execute_in_main_thread(self._startup_validations)

    def _startup_validations(self):
        """Run possible startup validations."""
        # Trigger version validation on start
        self._version_check_timer.timeout.emit()

        self._validate_settings_defaults()

        if not op_version_control_available():
            dialog = BuildVersionDialog()
            dialog.exec_()

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
            "Some default values in settings are missing. \n\n"
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
            msecs (int): Duration of message visibility in milliseconds.
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

        restart_action = QtWidgets.QAction(
            "Restart && Update", self.tray_widget
        )
        restart_action.triggered.connect(self._on_restart_action)
        restart_action.setVisible(False)

        self.tray_widget.menu.addAction(version_action)
        self.tray_widget.menu.addAction(restart_action)
        self.tray_widget.menu.addSeparator()

        self._restart_action = restart_action

    def _on_restart_action(self):
        self.restart(use_expected_version=True)

    def restart(self, use_expected_version=False, reset_version=False):
        """Restart Tray tool.

        First creates new process with same argument and close current tray.

        Args:
            use_expected_version(bool): OpenPype version is set to expected
                version.
            reset_version(bool): OpenPype version is cleaned up so igniters
                logic will decide which version will be used.
        """
        args = get_openpype_execute_args()
        kwargs = {
            "env": dict(os.environ.items())
        }

        # Create a copy of sys.argv
        additional_args = list(sys.argv)
        # Check last argument from `get_openpype_execute_args`
        # - when running from code it is the same as first from sys.argv
        if args[-1] == additional_args[0]:
            additional_args.pop(0)

        if use_expected_version:
            expected_version = get_expected_version()
            if expected_version is not None:
                reset_version = False
                kwargs["env"]["OPENPYPE_VERSION"] = str(expected_version)
            else:
                # Trigger reset of version if expected version was not found
                reset_version = True

        # Pop OPENPYPE_VERSION
        if reset_version:
            # Add staging flag if was running from staging
            if is_running_staging():
                args.append("--use-staging")
            kwargs["env"].pop("OPENPYPE_VERSION", None)

        args.extend(additional_args)
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
