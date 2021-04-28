# -*- coding: utf-8 -*-
"""Show dialog for choosing central pype repository."""
import os
import sys
import re

from Qt import QtCore, QtGui, QtWidgets  # noqa
from Qt.QtGui import QValidator  # noqa
from Qt.QtCore import QTimer  # noqa

from .install_thread import InstallThread, InstallResult
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
        point = self.mapToGlobal(self.rect().bottomLeft())
        self.options_menu.popup(point)

    def _on_trigger(self, action):
        self.option_clicked.emit(action.data())

    def _on_main_button(self):
        self.option_clicked.emit(self._default_value)


class MongoUrlInput(QtWidgets.QLineEdit):
    """Widget to input mongodb URL."""

    def set_valid(self):
        """Set valid state on mongo url input."""
        self.setProperty("state", "valid")
        # self.ensurePolished()
        self.style().polish(self)

    def set_invalid(self):
        """Set invalid state on mongo url input."""
        self.setProperty("state", "invalid")
        self.style().polish(self)


class InstallDialog(QtWidgets.QDialog):
    """Main Igniter dialog window."""

    mongo_url_regex = re.compile(r"(mongodb|mongodb+srv)://.+")

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
        self._openpype_run_ready = False
        self._controls_disabled = False
        self._install_thread = None

        # style for normal console text
        self.default_console_style = QtGui.QTextCharFormat()
        # self.default_console_style.setFontPointSize(0.1)
        self.default_console_style.setForeground(
            QtGui.QColor.fromRgb(72, 200, 150))

        # style for error console text
        self.error_console_style = QtGui.QTextCharFormat()
        # self.error_console_style.setFontPointSize(0.1)
        self.error_console_style.setForeground(
            QtGui.QColor.fromRgb(184, 54, 19))

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
        main_label.setStyleSheet("color: rgb(200, 200, 200);")

        # OpenPype path info
        # --------------------------------------------------------------------

        openpype_path_label = QtWidgets.QLabel(
            """<p>
            If you want to just try OpenPype without installing, hit the
            middle button that states "run without installation".
            </p>
            """,
            self
        )

        openpype_path_label.setWordWrap(True)
        openpype_path_label.setStyleSheet("color: rgb(150, 150, 150);")

        # Mongo box | OK button
        # --------------------------------------------------------------------

        mongo_label = QtWidgets.QLabel(
            """Enter URL for running MongoDB instance:"""
        )
        mongo_label.setWordWrap(True)
        mongo_label.setStyleSheet("color: rgb(150, 150, 150);")

        mongo_input = MongoUrlInput(self)
        # mongo_input = QtWidgets.QLineEdit(self)
        mongo_input.setPlaceholderText(
            "Mongo URL < mongodb://192.168.1.1:27017 >"
        )
        if self.mongo_url:
            mongo_input.setText(self.mongo_url)

        # Bottom button bar
        # --------------------------------------------------------------------
        bottom_widget = QtWidgets.QWidget(self)

        btns_widget = QtWidgets.QWidget(bottom_widget)

        openpype_logo_label = QtWidgets.QLabel("openpype logo", bottom_widget)
        openpype_logo_label.setPixmap(self._pixmap_openpype_logo)
        openpype_logo_label.setContentsMargins(10, 0, 0, 10)

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
        btns_layout.addWidget(run_button, 0)
        btns_layout.addWidget(exit_button, 0)

        bottom_layout = QtWidgets.QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 10, 10, 0)
        bottom_layout.setAlignment(QtCore.Qt.AlignVCenter)
        bottom_layout.addWidget(openpype_logo_label, 0)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(btns_widget, 0)

        # Console label
        # --------------------------------------------------------------------
        status_label = QtWidgets.QLabel("Console:", self)
        status_label.setContentsMargins(0, 10, 0, 10)
        status_label.setStyleSheet("color: rgb(61, 115, 97);")

        # Console
        # --------------------------------------------------------------------
        status_box = QtWidgets.QPlainTextEdit(self)
        status_box.setReadOnly(True)
        status_box.setCurrentCharFormat(self.default_console_style)
        status_box.setObjectName("Console")

        # Progress bar
        # --------------------------------------------------------------------
        progress_bar = QtWidgets.QProgressBar(self)
        progress_bar.setValue(0)
        progress_bar.setAlignment(QtCore.Qt.AlignCenter)
        progress_bar.setTextVisible(False)

        # add all to main
        main = QtWidgets.QVBoxLayout(self)
        main.addWidget(main_label, 0)
        main.addWidget(openpype_path_label, 0)
        main.addWidget(mongo_label, 0)
        main.addWidget(mongo_input, 0)

        main.addWidget(status_label, 0)
        main.addWidget(status_box, 1)

        main.addWidget(progress_bar, 0)
        main.addWidget(bottom_widget, 0)

        run_button.option_clicked.connect(self._on_run_btn_click)
        exit_button.clicked.connect(self._on_exit_clicked)
        mongo_input.textChanged.connect(self._on_mongo_url_change)

        self.main_label = main_label
        self.openpype_path_label = openpype_path_label
        self.mongo_label = mongo_label

        self._mongo_input = mongo_input

        self._status_label = status_label
        self._status_box = status_box

        self._run_button = run_button
        self._exit_button = exit_button
        self._progress_bar = progress_bar

    def _on_run_btn_click(self, option):
        if not self.validate_url():
            return

        if option == "Run":
            self._run_openpype()
        elif option == "Run from code":
            self._run_openpype_from_code()
        else:
            raise AssertionError("BUG: Unknown variant \"{}\"".format(option))

    def _run_openpype_from_code(self):
        valid, reason = validate_mongo_connection(self.mongo_url)
        if not valid:
            self._mongo_input.set_invalid()
            self.update_console(f"!!! {reason}", True)
            return
        else:
            self._mongo_input.set_valid()

        self.done(2)

    def _run_openpype(self):
        """Start install process.

        This will once again validate entered path and mongo if ok, start
        working thread that will do actual job.
        """
        # Check if install thread is not already running
        if self._install_thread and self._install_thread.isRunning():
            return

        valid, reason = validate_mongo_connection(self.mongo_url)
        if not valid:
            self._mongo_input.set_invalid()
            self.update_console(f"!!! {reason}", True)
            return
        else:
            self._mongo_input.set_valid()

        if self._openpype_run_ready:
            self.done(3)
            return

        if not valid:
            self.update_console(f"!!! {reason}", True)
            return

        self._disable_buttons()

        install_thread = InstallThread(self)
        install_thread.message.connect(self.update_console)
        install_thread.progress.connect(self._update_progress)
        install_thread.finished.connect(self._installation_finished)
        install_thread.set_mongo(self.mongo_url)

        self._install_thread = install_thread

        install_thread.start()

    def _installation_finished(self, status):
        self._enable_buttons()
        if status >= 0:
            self._openpype_run_ready = True
            self.done(3)

    def _update_progress(self, progress: int):
        self._progress_bar.setValue(progress)

    def _on_exit_clicked(self):
        self.reject()

    def _on_mongo_url_change(self, new_value):
        self.mongo_url = new_value
        if self.mongo_url_regex.match(new_value):
            self._mongo_input.set_valid()
        else:
            self._mongo_input.set_invalid()

    def validate_url(self):
        """Validate if entered url is ok.

        Returns:
            True if url is valid monogo string.

        """
        if self.mongo_url == "":
            return False

        is_valid, reason_str = validate_mongo_connection(self.mongo_url)
        if not is_valid:
            self._mongo_input.set_invalid()
            self.update_console(f"!!! {reason_str}", True)
            return False
        else:
            self._mongo_input.set_valid()
        return True

    def update_console(self, msg: str, error: bool = False) -> None:
        """Display message in console.

        Args:
            msg (str): message.
            error (bool): if True, print it red.
        """
        if not error:
            self._status_box.setCurrentCharFormat(self.default_console_style)
        else:
            self._status_box.setCurrentCharFormat(self.error_console_style)
        self._status_box.appendPlainText(msg)

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




class CollapsibleWidget(QtWidgets.QWidget):
    """Collapsible widget to hide mongo url in necessary."""

    def __init__(self, parent=None, title: str = "", animation: int = 300):
        self._mainLayout = QtWidgets.QGridLayout(parent)
        self._toggleButton = QtWidgets.QToolButton(parent)
        self._headerLine = QtWidgets.QFrame(parent)
        self._toggleAnimation = QtCore.QParallelAnimationGroup(parent)
        self._contentArea = QtWidgets.QScrollArea(parent)
        self._animation = animation
        self._title = title
        super(CollapsibleWidget, self).__init__(parent)
        self._init_ui()

    def _init_ui(self):
        self._toggleButton.setStyleSheet(
            """QToolButton {
                border: none;
                }
            """)
        self._toggleButton.setToolButtonStyle(
            QtCore.Qt.ToolButtonTextBesideIcon)

        self._toggleButton.setArrowType(QtCore.Qt.ArrowType.RightArrow)
        self._toggleButton.setText(self._title)
        self._toggleButton.setCheckable(True)
        self._toggleButton.setChecked(False)

        self._headerLine.setFrameShape(QtWidgets.QFrame.HLine)
        self._headerLine.setFrameShadow(QtWidgets.QFrame.Sunken)
        self._headerLine.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                       QtWidgets.QSizePolicy.Maximum)

        self._contentArea.setStyleSheet(
            """QScrollArea {
                background-color: rgb(32, 32, 32);
                border: none;
                }
            """)
        self._contentArea.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                                        QtWidgets.QSizePolicy.Fixed)
        self._contentArea.setMaximumHeight(0)
        self._contentArea.setMinimumHeight(0)

        self._toggleAnimation.addAnimation(
            QtCore.QPropertyAnimation(self, b"minimumHeight"))
        self._toggleAnimation.addAnimation(
            QtCore.QPropertyAnimation(self, b"maximumHeight"))
        self._toggleAnimation.addAnimation(
            QtCore.QPropertyAnimation(self._contentArea, b"maximumHeight"))

        self._mainLayout.setVerticalSpacing(0)
        self._mainLayout.setContentsMargins(0, 0, 0, 0)

        row = 0

        self._mainLayout.addWidget(
            self._toggleButton, row, 0, 1, 1, QtCore.Qt.AlignCenter)
        self._mainLayout.addWidget(
            self._headerLine, row, 2, 1, 1)
        row += row
        self._mainLayout.addWidget(self._contentArea, row, 0, 1, 3)
        self.setLayout(self._mainLayout)

        self._toggleButton.toggled.connect(self._toggle_action)

    def _toggle_action(self, collapsed: bool):
        arrow = QtCore.Qt.ArrowType.DownArrow if collapsed else QtCore.Qt.ArrowType.RightArrow  # noqa: E501
        direction = QtCore.QAbstractAnimation.Forward if collapsed else QtCore.QAbstractAnimation.Backward  # noqa: E501
        self._toggleButton.setArrowType(arrow)
        self._toggleAnimation.setDirection(direction)
        self._toggleAnimation.start()

    def setContentLayout(self, content_layout: QtWidgets.QLayout):  # noqa
        self._contentArea.setLayout(content_layout)
        collapsed_height = \
            self.sizeHint().height() - self._contentArea.maximumHeight()
        content_height = self._contentArea.sizeHint().height()

        for i in range(self._toggleAnimation.animationCount() - 1):
            sec_anim = self._toggleAnimation.animationAt(i)
            sec_anim.setDuration(self._animation)
            sec_anim.setStartValue(collapsed_height)
            sec_anim.setEndValue(collapsed_height + content_height)

        con_anim = self._toggleAnimation.animationAt(
            self._toggleAnimation.animationCount() - 1)

        con_anim.setDuration(self._animation)
        con_anim.setStartValue(0)
        con_anim.setEndValue(collapsed_height + content_height)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    d = InstallDialog()
    d.show()
    sys.exit(app.exec_())
