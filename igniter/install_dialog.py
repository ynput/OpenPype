# -*- coding: utf-8 -*-
"""Show dialog for choosing central pype repository."""
import os
import sys

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


class FocusHandlingLineEdit(QtWidgets.QLineEdit):
    """Handling focus in/out on QLineEdit."""
    focusIn = QtCore.Signal()
    focusOut = QtCore.Signal()

    def focusOutEvent(self, event):  # noqa
        """For emitting signal on focus out."""
        self.focusOut.emit()
        super().focusOutEvent(event)

    def focusInEvent(self, event):  # noqa
        """For emitting signal on focus in."""
        self.focusIn.emit()
        super().focusInEvent(event)


class MongoWidget(QtWidgets.QWidget):
    """Widget to input mongodb URL."""

    def __init__(self, parent=None):
        super(MongoWidget, self).__init__(parent)

        self._mongo_input = FocusHandlingLineEdit(self)
        self._mongo_input.setPlaceholderText("Mongo URL")
        self._mongo_input.textChanged.connect(self._mongo_changed)
        self._mongo_input.focusIn.connect(self._focus_in)
        self._mongo_input.focusOut.connect(self._focus_out)
        self._mongo_input.setValidator(
            MongoValidator(self._mongo_input))
        self._mongo_input.setStyleSheet(
            ("color: rgb(233, 233, 233);"
             "background-color: rgb(64, 64, 64);"
             "padding: 0.5em;"
             "border: 1px solid rgb(32, 32, 32);")
        )

        mongo_layout = QtWidgets.QHBoxLayout(self)
        mongo_layout.setContentsMargins(0, 0, 0, 0)

        mongo_layout.addWidget(self._mongo_input)

    def _focus_out(self):
        self.validate_url()

    def _focus_in(self):
        self._mongo_input.setStyleSheet(
            """
            background-color: rgb(32, 32, 19);
            color: rgb(255, 190, 15);
            padding: 0.5em;
            border: 1px solid rgb(64, 64, 32);
            """
        )

    def _mongo_changed(self, mongo: str):
        self.parent().mongo_url = mongo

    def get_mongo_url(self) -> str:
        """Helper to get url from parent."""
        return self.parent().mongo_url

    def set_mongo_url(self, mongo: str):
        """Helper to set url to  parent.

        Args:
            mongo (str): mongodb url string.

        """
        self._mongo_input.setText(mongo)

    def set_valid(self):
        """Set valid state on mongo url input."""
        self._mongo_input.setStyleSheet(
            """
            background-color: rgb(19, 19, 19);
            color: rgb(64, 230, 132);
            padding: 0.5em;
            border: 1px solid rgb(32, 64, 32);
            """
        )
        self.parent().install_button.setEnabled(True)

    def set_invalid(self):
        """Set invalid state on mongo url input."""
        self._mongo_input.setStyleSheet(
            """
            background-color: rgb(32, 19, 19);
            color: rgb(255, 69, 0);
            padding: 0.5em;
            border: 1px solid rgb(64, 32, 32);
            """
        )
        self.parent().install_button.setEnabled(False)

    def set_read_only(self, state: bool):
        """Set input read-only."""
        self._mongo_input.setReadOnly(state)

    def validate_url(self) -> bool:
        """Validate if entered url is ok.

        Returns:
            True if url is valid monogo string.

        """
        if self.parent().mongo_url == "":
            return False

        is_valid, reason_str = validate_mongo_connection(
            self.parent().mongo_url
        )
        if not is_valid:
            self.set_invalid()
            self.parent().update_console(f"!!! {reason_str}", True)
            return False
        else:
            self.set_valid()
        return True


class InstallDialog(QtWidgets.QDialog):
    """Main Igniter dialog window."""
    _controls_disabled = False

    def __init__(self, parent=None):
        super(InstallDialog, self).__init__(parent)
        self.secure_registry = OpenPypeSecureRegistry("mongodb")

        self.mongo_url = ""
        try:
            self.mongo_url = (
                os.getenv("OPENPYPE_MONGO", "")
                or self.secure_registry.get_item("openPypeMongo")
            )
        except ValueError:
            pass

        self.setWindowTitle(
            f"OpenPype Igniter {__version__} - OpenPype installation"
        )
        icon_path = os.path.join(
            os.path.dirname(__file__), 'openpype_icon.png'
        )
        pixmap_openpype_logo = QtGui.QPixmap(icon_path)

        self.setWindowIcon(QtGui.QIcon(pixmap_openpype_logo))
        self.setWindowFlags(
            QtCore.Qt.WindowCloseButtonHint |
            QtCore.Qt.WindowMinimizeButtonHint
        )

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

        QtGui.QFontDatabase.addApplicationFont(
            os.path.join(
                os.path.dirname(__file__), 'RobotoMono-Regular.ttf')
        )
        self._openpype_run_ready = False

        self._pixmap_openpype_logo = pixmap_openpype_logo

        self._init_ui()

        # Trigger mongo validation
        self._mongo_widget.validate_url()

    def _init_ui(self):
        # basic visual style - dark background, light text
        self.setStyleSheet("""
            color: rgb(200, 200, 200);
            background-color: rgb(23, 23, 23);
        """)

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

        mongo_widget = MongoWidget(self)
        if self.mongo_url:
            mongo_widget.set_mongo_url(self.mongo_url)

        # Bottom button bar
        # --------------------------------------------------------------------
        bottom_widget = QtWidgets.QWidget(self)
        bottom_widget.setStyleSheet("background-color: rgb(32, 32, 32);")

        openpype_logo_label = QtWidgets.QLabel("openpype logo", bottom_widget)
        # openpype_logo.scaled(
        #     openpype_logo_label.width(),
        #     openpype_logo_label.height(), QtCore.Qt.KeepAspectRatio)
        openpype_logo_label.setPixmap(self._pixmap_openpype_logo)
        openpype_logo_label.setContentsMargins(10, 0, 0, 10)

        # install button - - - - - - - - - - - - - - - - - - - - - - - - - - -
        install_button = QtWidgets.QPushButton("Install", bottom_widget)
        install_button.setStyleSheet(
            ("color: rgb(64, 64, 64);"
             "background-color: rgb(72, 200, 150);"
             "padding: 0.5em;")
        )
        install_button.setMinimumSize(64, 24)
        install_button.setToolTip("Install OpenPype")

        # run from current button - - - - - - - - - - - - - - - - - - - - - -
        run_button = QtWidgets.QPushButton(
            "Run without installation", bottom_widget
        )
        run_button.setStyleSheet(
            ("color: rgb(64, 64, 64);"
             "background-color: rgb(200, 164, 64);"
             "padding: 0.5em;")
        )
        run_button.setMinimumSize(64, 24)
        run_button.setToolTip("Run without installing Pype")

        # install button - - - - - - - - - - - - - - - - - - - - - - - - - - -
        exit_button = QtWidgets.QPushButton("Exit", bottom_widget)
        exit_button.setStyleSheet(
            ("color: rgb(64, 64, 64);"
             "background-color: rgb(128, 128, 128);"
             "padding: 0.5em;")
        )
        exit_button.setMinimumSize(64, 24)
        exit_button.setToolTip("Exit")

        bottom_layout = QtWidgets.QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 10, 10, 0)
        bottom_layout.setAlignment(QtCore.Qt.AlignVCenter)
        bottom_layout.addWidget(openpype_logo_label, 0, QtCore.Qt.AlignVCenter)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(install_button, 0, QtCore.Qt.AlignVCenter)
        bottom_layout.addWidget(run_button, 0, QtCore.Qt.AlignVCenter)
        bottom_layout.addWidget(exit_button, 0, QtCore.Qt.AlignVCenter)

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
        status_box.setStyleSheet(
            """QPlainTextEdit {
                background-color: rgb(32, 32, 32);
                color: rgb(72, 200, 150);
                font-family: "Roboto Mono";
                font-size: 0.5em;
                border: 1px solid rgb(48, 48, 48);
                }
                QScrollBar:vertical {
                 border: 1px solid rgb(61, 115, 97);
                 background: #000;
                 width:5px;
                 margin: 0px 0px 0px 0px;
                }
                QScrollBar::handle:vertical {
                 background: rgb(72, 200, 150);
                 min-height: 0px;
                }
                QScrollBar::sub-page:vertical {
                 background: rgb(31, 62, 50);
                }
                QScrollBar::add-page:vertical {
                 background: rgb(31, 62, 50);
                }
                QScrollBar::add-line:vertical {
                 background: rgb(72, 200, 150);
                 height: 0px;
                 subcontrol-position: bottom;
                 subcontrol-origin: margin;
                }
                QScrollBar::sub-line:vertical {
                 background: rgb(72, 200, 150);
                 height: 0 px;
                 subcontrol-position: top;
                 subcontrol-origin: margin;
                }
            """
        )

        # Progress bar
        # --------------------------------------------------------------------
        progress_bar = QtWidgets.QProgressBar(self)
        progress_bar.setValue(0)
        progress_bar.setAlignment(QtCore.Qt.AlignCenter)
        progress_bar.setTextVisible(False)
        # setting font and the size
        progress_bar.setFont(QtGui.QFont('Arial', 7))
        progress_bar.setStyleSheet(
            """QProgressBar:horizontal {
                height: 5px;
                border: 1px solid rgb(31, 62, 50);
                color: rgb(72, 200, 150);
               }
               QProgressBar::chunk:horizontal {
               background-color: rgb(72, 200, 150);
               }
            """
        )
        # add all to main
        main = QtWidgets.QVBoxLayout(self)
        main.addWidget(main_label, 0)
        main.addWidget(openpype_path_label, 0)
        main.addWidget(mongo_label, 0)
        main.addWidget(mongo_widget, 0)

        main.addWidget(status_label, 0)
        main.addWidget(status_box, 1)

        main.addWidget(progress_bar, 0)
        main.addWidget(bottom_widget, 0)

        run_button.clicked.connect(self._on_run_clicked)
        install_button.clicked.connect(self._on_ok_clicked)
        exit_button.clicked.connect(self._on_exit_clicked)

        self.main_label = main_label
        self.openpype_path_label = openpype_path_label
        self.mongo_label = mongo_label

        self._mongo_widget = mongo_widget

        self._status_label = status_label
        self._status_box = status_box

        self.install_button = install_button
        self.run_button = run_button
        self._exit_button = exit_button
        self._progress_bar = progress_bar

    def _on_run_clicked(self):
        valid, reason = validate_mongo_connection(
            self._mongo_widget.get_mongo_url()
        )
        if not valid:
            self._mongo_widget.set_invalid()
            self.update_console(f"!!! {reason}", True)
            return
        else:
            self._mongo_widget.set_valid()

        self.done(2)

    def _on_ok_clicked(self):
        """Start install process.

        This will once again validate entered path and mongo if ok, start
        working thread that will do actual job.
        """
        valid, reason = validate_mongo_connection(
            self._mongo_widget.get_mongo_url()
        )
        if not valid:
            self._mongo_widget.set_invalid()
            self.update_console(f"!!! {reason}", True)
            return
        else:
            self._mongo_widget.set_valid()

        if self._openpype_run_ready:
            self.done(3)
            return

        if not valid:
            self.update_console(f"!!! {reason}", True)
            return

        self._disable_buttons()
        self._install_thread = InstallThread(
            self.install_result_callback_handler, self)
        self._install_thread.message.connect(self.update_console)
        self._install_thread.progress.connect(self._update_progress)
        self._install_thread.finished.connect(self._enable_buttons)
        self._install_thread.set_mongo(self._mongo_widget.get_mongo_url())
        self._install_thread.start()

    def install_result_callback_handler(self, result: InstallResult):
        """Change button behaviour based on installation outcome."""
        status = result.status
        if status >= 0:
            self.install_button.setText("Run installed OpenPype")
            self._openpype_run_ready = True

    def _update_progress(self, progress: int):
        self._progress_bar.setValue(progress)

    def _on_exit_clicked(self):
        self.reject()

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
        self.run_button.setEnabled(False)
        self._exit_button.setEnabled(False)
        self.install_button.setEnabled(False)
        self._controls_disabled = True

    def _enable_buttons(self):
        """Enable buttons after operation is complete."""
        self.run_button.setEnabled(True)
        self._exit_button.setEnabled(True)
        self.install_button.setEnabled(True)
        self._controls_disabled = False

    def closeEvent(self, event):  # noqa
        """Prevent closing if window when controls are disabled."""
        if self._controls_disabled:
            return event.ignore()
        return super(InstallDialog, self).closeEvent(event)


class MongoValidator(QValidator):
    """Validate mongodb url for Qt widgets."""

    def __init__(self, parent=None, intermediate=False):
        self.parent = parent
        self.intermediate = intermediate
        self._validate_lock = False
        self.timer = QTimer()
        self.timer.timeout.connect(self._unlock_validator)
        super().__init__(parent)

    def _unlock_validator(self):
        self._validate_lock = False

    def _return_state(
            self, state: QValidator.State, reason: str, mongo: str):
        """Set stylesheets and actions on parent based on state.

        Warning:
            This will always return `QValidator.State.Acceptable` as
            anything different will stop input to `QLineEdit`

        """

        if state == QValidator.State.Invalid:
            self.parent.setToolTip(reason)
            self.parent.setStyleSheet(
                """
                background-color: rgb(32, 19, 19);
                color: rgb(255, 69, 0);
                padding: 0.5em;
                border: 1px solid rgb(64, 32, 32);
                """
            )
        elif state == QValidator.State.Intermediate and self.intermediate:
            self.parent.setToolTip(reason)
            self.parent.setStyleSheet(
                """
                background-color: rgb(32, 32, 19);
                color: rgb(255, 190, 15);
                padding: 0.5em;
                border: 1px solid rgb(64, 64, 32);
                """
            )
        else:
            self.parent.setToolTip(reason)
            self.parent.setStyleSheet(
                """
                background-color: rgb(19, 19, 19);
                color: rgb(64, 230, 132);
                padding: 0.5em;
                border: 1px solid rgb(32, 64, 32);
                """
            )

        return QValidator.State.Acceptable, mongo, len(mongo)

    def validate(self, mongo: str, pos: int) -> (QValidator.State, str, int):    # noqa
        """Validate entered mongodb connection string.

        As url (it should start with `mongodb://` or
        `mongodb+srv:// url schema.

        Args:
            mongo (str): connection string url.
            pos (int): current position.

        Returns:
            (QValidator.State.Acceptable, str, int):
                Indicate input state with color and always return
                Acceptable state as we need to be able to edit input further.

        """
        if not mongo.startswith("mongodb"):
            return self._return_state(
                QValidator.State.Invalid, "need mongodb schema", mongo)

        return self._return_state(
            QValidator.State.Intermediate, "", mongo)




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
