# -*- coding: utf-8 -*-
"""Show dialog for choosing central pype repository."""
import os
import sys
import re

from Qt import QtCore, QtGui, QtWidgets  # noqa
from Qt.QtGui import QValidator  # noqa
from Qt.QtCore import QTimer  # noqa

from .install_thread import InstallThread
from .tools import (
    validate_mongo_connection,
    get_openpype_path_from_db
)
from .user_settings import OpenPypeSecureRegistry
from .version import __version__


def load_stylesheet():
    stylesheet_path = os.path.join(
        os.path.dirname(__file__),
        "stylesheet.css"
    )
    with open(stylesheet_path, "r") as file_stream:
        stylesheet = file_stream.read()

    return stylesheet


class ButtonWithOptions(QtWidgets.QFrame):
    option_clicked = QtCore.Signal(str)

    def __init__(self, options, default=None, parent=None):
        super(ButtonWithOptions, self).__init__(parent)

        self.setObjectName("ButtonWithOptions")

        if default:
            if default not in options:
                default = None

        if default is None:
            default = options[0]

        main_btn = QtWidgets.QPushButton(default, self)
        main_btn.setFlat(True)

        options_btn = QtWidgets.QToolButton(self)
        options_btn.setArrowType(QtCore.Qt.DownArrow)
        options_btn.setIconSize(QtCore.QSize(12, 12))

        options_menu = QtWidgets.QMenu(self)
        for option in options:
            action = QtWidgets.QAction(option, options_menu)
            action.setData(option)
            options_menu.addAction(action)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(1)

        main_layout.addWidget(main_btn, 1, QtCore.Qt.AlignVCenter)
        main_layout.addWidget(options_btn, 0, QtCore.Qt.AlignVCenter)

        main_btn.clicked.connect(self._on_main_button)
        options_btn.clicked.connect(self._on_options_click)
        options_menu.triggered.connect(self._on_trigger)

        self.main_btn = main_btn
        self.options_btn = options_btn
        self.options_menu = options_menu

        self._default_value = default

    def resizeEvent(self, event):
        super(ButtonWithOptions, self).resizeEvent(event)
        self.options_btn.setFixedHeight(self.main_btn.height())

    def _on_options_click(self):
        pos = self.main_btn.rect().bottomLeft()
        point = self.main_btn.mapToGlobal(pos)
        self.options_menu.popup(point)

    def _on_trigger(self, action):
        self.option_clicked.emit(action.data())

    def _on_main_button(self):
        self.option_clicked.emit(self._default_value)


class ConsoleWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(ConsoleWidget, self).__init__(parent)

        # style for normal and error console text
        default_console_style = QtGui.QTextCharFormat()
        error_console_style = QtGui.QTextCharFormat()
        default_console_style.setForeground(
            QtGui.QColor.fromRgb(72, 200, 150)
        )
        error_console_style.setForeground(
            QtGui.QColor.fromRgb(184, 54, 19)
        )

        separator = QtWidgets.QWidget(self)
        separator.setMinimumHeight(2)
        separator.setObjectName("Separator")

        label = QtWidgets.QLabel("Console:", self)

        console_output = QtWidgets.QPlainTextEdit(self)
        console_output.setMinimumSize(QtCore.QSize(300, 200))
        console_output.setReadOnly(True)
        console_output.setCurrentCharFormat(default_console_style)
        console_output.setObjectName("Console")

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(separator, 0)
        main_layout.addWidget(label, 0)
        main_layout.addWidget(console_output, 1)

        self.default_console_style = default_console_style
        self.error_console_style = error_console_style

        self.separator = separator
        self.label = label
        self.console_output = console_output

        self.hide_console()

    def hide_console(self):
        self.separator.setVisible(False)
        self.label.setVisible(False)
        self.console_output.setVisible(False)

        self.updateGeometry()

    def show_console(self):
        self.separator.setVisible(True)
        self.label.setVisible(True)
        self.console_output.setVisible(True)

        self.updateGeometry()

    def update_console(self, msg: str, error: bool = False) -> None:
        if not error:
            self.console_output.setCurrentCharFormat(
                self.default_console_style
            )
        else:
            self.console_output.setCurrentCharFormat(
                self.error_console_style
            )
        self.console_output.appendPlainText(msg)


class MongoUrlInput(QtWidgets.QLineEdit):
    """Widget to input mongodb URL."""

    def set_valid(self):
        """Set valid state on mongo url input."""
        self.setProperty("state", "valid")
        self.style().polish(self)

    def set_warning(self):
        """Set invalid state on mongo url input."""
        self.setProperty("state", "warning")
        self.style().polish(self)

    def set_invalid(self):
        """Set invalid state on mongo url input."""
        self.setProperty("state", "invalid")
        self.style().polish(self)


class InstallDialog(QtWidgets.QDialog):
    """Main Igniter dialog window."""

    mongo_url_regex = re.compile(r"(mongodb|mongodb\+srv)://.+")

    _width = 300
    _height = 200
    def __init__(self, parent=None):
        super(InstallDialog, self).__init__(parent)

        self.setWindowTitle(
            f"OpenPype Igniter {__version__} - OpenPype installation"
        )
        self.setWindowFlags(
            QtCore.Qt.WindowCloseButtonHint
            | QtCore.Qt.WindowMinimizeButtonHint
        )

        current_dir = os.path.dirname(os.path.abspath(__file__))
        roboto_font_path = os.path.join(current_dir, "RobotoMono-Regular.ttf")
        icon_path = os.path.join(current_dir, "openpype_icon.png")

        # Install roboto font
        QtGui.QFontDatabase.addApplicationFont(roboto_font_path)

        # Load logo
        pixmap_openpype_logo = QtGui.QPixmap(icon_path)
        # Set logo as icon of window
        self.setWindowIcon(QtGui.QIcon(pixmap_openpype_logo))

        secure_registry = OpenPypeSecureRegistry("mongodb")
        mongo_url = ""
        try:
            mongo_url = (
                os.getenv("OPENPYPE_MONGO", "")
                or secure_registry.get_item("openPypeMongo")
            )
        except ValueError:
            pass

        self.mongo_url = mongo_url
        self._pixmap_openpype_logo = pixmap_openpype_logo

        self._secure_registry = secure_registry
        self._controls_disabled = False
        self._install_thread = None

        self.setMinimumSize(QtCore.QSize(self._width, self._height))
        self._init_ui()

        # Set stylesheet
        self.setStyleSheet(load_stylesheet())

        # Trigger mongo validation
        self.validate_url()

    def _init_ui(self):
        # basic visual style - dark background, light text

        # Main info
        # --------------------------------------------------------------------
        main_label = QtWidgets.QLabel("Welcome to <b>OpenPype</b>", self)
        main_label.setWordWrap(True)
        main_label.setObjectName("MainLabel")

        # Mongo box | OK button
        # --------------------------------------------------------------------
        mongo_label = QtWidgets.QLabel("Enter your Mongo URL:")
        mongo_label.setWordWrap(True)

        mongo_input = MongoUrlInput(self)
        mongo_input.setPlaceholderText(
            "Mongo URL < mongodb://192.168.1.1:27017 >"
        )
        if self.mongo_url:
            mongo_input.setText(self.mongo_url)

        mongo_messages_widget = QtWidgets.QWidget(self)
        mongo_connection_msg = QtWidgets.QLabel(mongo_messages_widget)
        mongo_url_msg = QtWidgets.QLabel(mongo_messages_widget)

        mongo_url_msg.setVisible(False)
        mongo_connection_msg.setVisible(False)

        mongo_messages_layout = QtWidgets.QVBoxLayout(mongo_messages_widget)
        mongo_messages_layout.setContentsMargins(0, 0, 0, 0)
        mongo_messages_layout.addWidget(mongo_connection_msg)
        mongo_messages_layout.addWidget(mongo_url_msg)
        progress_separator = QtWidgets.QWidget(self)
        progress_separator.setMinimumHeight(2)
        progress_separator.setObjectName("Separator")

        # Bottom button bar
        # --------------------------------------------------------------------
        bottom_widget = QtWidgets.QWidget(self)

        btns_widget = QtWidgets.QWidget(bottom_widget)

        openpype_logo_label = QtWidgets.QLabel("openpype logo", bottom_widget)
        openpype_logo_label.setPixmap(self._pixmap_openpype_logo)
        openpype_logo_label.setContentsMargins(5, 5, 5, 5)

        run_button = ButtonWithOptions(
            ["Run", "Run from code"],
            "Run",
            btns_widget
        )
        run_button.setMinimumSize(64, 24)
        run_button.setToolTip("Run OpenPype")

        # install button - - - - - - - - - - - - - - - - - - - - - - - - - - -
        exit_button = QtWidgets.QPushButton("Exit", btns_widget)
        exit_button.setObjectName("ExitBtn")
        exit_button.setFlat(True)
        exit_button.setMinimumSize(64, 24)
        exit_button.setToolTip("Exit")

        btns_layout = QtWidgets.QHBoxLayout(btns_widget)
        btns_layout.setContentsMargins(0, 0, 0, 0)
        btns_layout.addWidget(run_button, 0)
        btns_layout.addWidget(exit_button, 0)

        bottom_layout = QtWidgets.QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setAlignment(QtCore.Qt.AlignHCenter)
        bottom_layout.addWidget(openpype_logo_label, 0)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(btns_widget, 0)

        # Console
        # --------------------------------------------------------------------
        console_widget = ConsoleWidget(self)

        # Progress bar
        # --------------------------------------------------------------------
        progress_bar = QtWidgets.QProgressBar(self)
        progress_bar.setValue(0)
        progress_bar.setAlignment(QtCore.Qt.AlignCenter)
        progress_bar.setTextVisible(False)

        # add all to main
        main = QtWidgets.QVBoxLayout(self)
        main.addWidget(main_label, 0)
        main.addWidget(mongo_label, 0)
        main.addWidget(mongo_input, 0)
        main.addWidget(mongo_messages_widget, 0)

        main.addWidget(progress_separator, 0)
        main.addWidget(progress_bar, 0)

        main.addWidget(console_widget, 1)

        main.addWidget(bottom_widget, 0)

        run_button.option_clicked.connect(self._on_run_btn_click)
        exit_button.clicked.connect(self._on_exit_clicked)
        mongo_input.textChanged.connect(self._on_mongo_url_change)

        self._console_widget = console_widget

        self.main_label = main_label

        self.mongo_label = mongo_label
        self._mongo_input = mongo_input

        self._mongo_connection_msg = mongo_connection_msg
        self._mongo_url_msg = mongo_url_msg

        self._run_button = run_button
        self._exit_button = exit_button
        self._progress_bar = progress_bar

    def _on_run_btn_click(self, option):
        # Disable buttons
        self._disable_buttons()
        # Set progress to any value
        self._update_progress(1)
        self._progress_bar.repaint()
        # Process events to repaint changes
        QtWidgets.QApplication.processEvents()

        if not self.validate_url():
            self._enable_buttons()
            self._update_progress(0)
            return

        if option == "Run":
            self._run_openpype()
        elif option == "Run from code":
            self._run_openpype_from_code()
        else:
            raise AssertionError("BUG: Unknown variant \"{}\"".format(option))

        self._enable_buttons()

    def _run_openpype_from_code(self):
        self._secure_registry.set_item("openPypeMongo", self.mongo_url)

        self.done(2)

    def _run_openpype(self):
        """Start install process.

        This will once again validate entered path and mongo if ok, start
        working thread that will do actual job.
        """
        # Check if install thread is not already running
        if self._install_thread and self._install_thread.isRunning():
            return

        self._mongo_input.set_valid()

        install_thread = InstallThread(self)
        install_thread.message.connect(self.update_console)
        install_thread.progress.connect(self._update_progress)
        install_thread.finished.connect(self._installation_finished)
        install_thread.set_mongo(self.mongo_url)

        self._install_thread = install_thread

        install_thread.start()

    def _installation_finished(self, status):
        if status >= 0:
            self._update_progress(100)
            self.done(3)
        else:
            self._show_console()

    def _update_progress(self, progress: int):
        self._progress_bar.setValue(progress)

    def _on_exit_clicked(self):
        self.reject()

    def _on_mongo_url_change(self, new_value):
        # Strip the value
        new_value = new_value.strip()
        # Store new mongo url to variable
        self.mongo_url = new_value

        msg = None
        # Change style of input
        if not new_value:
            self._mongo_input.set_warning()
        elif not self.mongo_url_regex.match(new_value):
            self._mongo_input.set_invalid()
            msg = (
                "Invalid Mongo URL should start with"
                " \"mongodb://\" or \"mongodb+srv://\""
            )
        else:
            self._mongo_input.set_valid()

        self.set_invalid_mongo_url(msg)

    def validate_url(self):
        """Validate if entered url is ok.

        Returns:
            True if url is valid monogo string.

        """
        if self.mongo_url == "":
            return False

        is_valid, reason_str = validate_mongo_connection(self.mongo_url)
        if not is_valid:
            self.set_invalid_mongo_connection(self.mongo_url)
            self._mongo_input.set_warning()
            self.update_console(f"!!! {reason_str}", True)
            return False

        self.set_invalid_mongo_connection(None)
        self._mongo_input.set_valid()
        return True

    def set_invalid_mongo_url(self, reason):
        if reason is None:
            self._mongo_url_msg.setVisible(False)
        else:
            self._mongo_url_msg.setVisible(True)
            self._mongo_url_msg.setText("- {}".format(reason))

    def set_invalid_mongo_connection(self, mongo_url):
        if mongo_url is None:
            self._mongo_connection_msg.setVisible(False)
        else:
            self._mongo_connection_msg.setText(
                "- Can't connect to: <b>{}</b>".format(mongo_url)
            )
            self._mongo_connection_msg.setVisible(True)

    def update_console(self, msg: str, error: bool = False) -> None:
        """Display message in console.

        Args:
            msg (str): message.
            error (bool): if True, print it red.
        """
        self._console_widget.update_console(msg, error)

    def _show_console(self):
        self._console_widget.show_console()
        self.updateGeometry()

    def _disable_buttons(self):
        """Disable buttons so user interaction doesn't interfere."""
        self._exit_button.setEnabled(False)
        self._run_button.setEnabled(False)
        self._controls_disabled = True

    def _enable_buttons(self):
        """Enable buttons after operation is complete."""
        self._exit_button.setEnabled(True)
        self._run_button.setEnabled(True)
        self._controls_disabled = False

    def closeEvent(self, event):  # noqa
        """Prevent closing if window when controls are disabled."""
        if self._controls_disabled:
            return event.ignore()
        return super(InstallDialog, self).closeEvent(event)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    d = InstallDialog()
    d.show()
    sys.exit(app.exec_())
