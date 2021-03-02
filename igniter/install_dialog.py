# -*- coding: utf-8 -*-
"""Show dialog for choosing central pype repository."""
import os
import sys

from Qt import QtCore, QtGui, QtWidgets  # noqa
from Qt.QtGui import QValidator  # noqa

from .install_thread import InstallThread
from .tools import (
    validate_path_string,
    validate_mongo_connection,
    get_pype_path_from_db
)
from .user_settings import PypeSettingsRegistry


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


class InstallDialog(QtWidgets.QDialog):
    """Main Igniter dialog window."""
    _size_w = 400
    _size_h = 600
    path = None
    _controls_disabled = False

    def __init__(self, parent=None):
        super(InstallDialog, self).__init__(parent)
        self.registry = PypeSettingsRegistry()

        self.mongo_url = os.getenv("PYPE_MONGO", "") or self.registry.get_secure_item("pypeMongo") or ""  # noqa: E501

        self.setWindowTitle("Pype - Configure Pype repository path")
        self._icon_path = os.path.join(
            os.path.dirname(__file__), 'pype_icon.png')
        icon = QtGui.QIcon(self._icon_path)
        self.setWindowIcon(icon)
        self.setWindowFlags(
            QtCore.Qt.WindowCloseButtonHint |
            QtCore.Qt.WindowMinimizeButtonHint
        )

        self.setMinimumSize(
            QtCore.QSize(self._size_w, self._size_h))
        self.setMaximumSize(
            QtCore.QSize(self._size_w + 100, self._size_h + 500))

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

        self._init_ui()

    def _init_ui(self):
        # basic visual style - dark background, light text
        self.setStyleSheet("""
            color: rgb(200, 200, 200);
            background-color: rgb(23, 23, 23);
        """)

        main = QtWidgets.QVBoxLayout(self)

        # Main info
        # --------------------------------------------------------------------
        self.main_label = QtWidgets.QLabel(
            """Welcome to <b>Pype</b>
            <p>
            We've detected <b>Pype</b> is not configured yet. But don't worry,
            this is as easy as setting one thing.
            <p>
            """)
        self.main_label.setWordWrap(True)
        self.main_label.setStyleSheet("color: rgb(200, 200, 200);")

        # Pype path info
        # --------------------------------------------------------------------

        self.pype_path_label = QtWidgets.QLabel(
            """This can be either <b>Path to studio location</b>
            or <b>Database connection string</b> or <b>Pype Token</b>.
            <p>
            Leave it empty if you want to use Pype version that come with this
            installation.
            </p>
            """
        )

        self.pype_path_label.setWordWrap(True)
        self.pype_path_label.setStyleSheet("color: rgb(150, 150, 150);")

        # Path/Url box | Select button
        # --------------------------------------------------------------------

        input_layout = QtWidgets.QHBoxLayout()

        input_layout.setContentsMargins(0, 10, 0, 10)
        self.user_input = FocusHandlingLineEdit()

        self.user_input.setPlaceholderText("Pype repository path or url")
        self.user_input.textChanged.connect(self._path_changed)
        self.user_input.setStyleSheet(
            ("color: rgb(233, 233, 233);"
             "background-color: rgb(64, 64, 64);"
             "padding: 0.5em;"
             "border: 1px solid rgb(32, 32, 32);")
        )

        self.user_input.setValidator(PathValidator(self.user_input))

        self._btn_select = QtWidgets.QPushButton("Select")
        self._btn_select.setToolTip(
            "Select Pype repository"
        )
        self._btn_select.setStyleSheet(
            ("color: rgb(64, 64, 64);"
             "background-color: rgb(72, 200, 150);"
             "padding: 0.5em;")
        )
        self._btn_select.setMaximumSize(100, 140)
        self._btn_select.clicked.connect(self._on_select_clicked)

        input_layout.addWidget(self.user_input)
        input_layout.addWidget(self._btn_select)

        # Mongo box | OK button
        # --------------------------------------------------------------------

        class MongoWidget(QtWidgets.QWidget):
            """Widget to input mongodb URL."""

            def __init__(self, parent=None):
                self._btn_mongo = None
                super(MongoWidget, self).__init__(parent)
                mongo_layout = QtWidgets.QHBoxLayout()
                mongo_layout.setContentsMargins(0, 0, 0, 0)
                self._mongo_input = FocusHandlingLineEdit()
                self._mongo_input.setPlaceholderText("Mongo URL")
                self._mongo_input.textChanged.connect(self._mongo_changed)
                self._mongo_input.focusIn.connect(self._focus_in)
                self._mongo_input.focusOut.connect(self._focus_out)
                # self._mongo_input.setValidator(
                #     PathValidator(self._mongo_input))
                self._mongo_input.setStyleSheet(
                    ("color: rgb(233, 233, 233);"
                     "background-color: rgb(64, 64, 64);"
                     "padding: 0.5em;"
                     "border: 1px solid rgb(32, 32, 32);")
                )

                mongo_layout.addWidget(self._mongo_input)
                self.setLayout(mongo_layout)

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
                self.parent().ok_button.setEnabled(True)
                if self.parent().path != "":
                    path = get_pype_path_from_db(self.parent().mongo_url)
                    self.parent().path = path
                    self.parent().user_input.setText(path)

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
                self.parent().ok_button.setEnabled(False)

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

        self._mongo = MongoWidget(self)
        if self.mongo_url:
            self._mongo.set_mongo_url(self.mongo_url)

        # Bottom button bar
        # --------------------------------------------------------------------
        bottom_widget = QtWidgets.QWidget()
        bottom_layout = QtWidgets.QHBoxLayout()
        pype_logo_label = QtWidgets.QLabel("pype logo")
        pype_logo = QtGui.QPixmap(self._icon_path)
        # pype_logo.scaled(
        #     pype_logo_label.width(),
        #     pype_logo_label.height(), QtCore.Qt.KeepAspectRatio)
        pype_logo_label.setPixmap(pype_logo)
        pype_logo_label.setContentsMargins(10, 0, 0, 10)

        self.ok_button = QtWidgets.QPushButton("OK")
        self.ok_button.setStyleSheet(
            ("color: rgb(64, 64, 64);"
             "background-color: rgb(72, 200, 150);"
             "padding: 0.5em;")
        )
        self.ok_button.setMinimumSize(64, 24)
        self.ok_button.setToolTip("Save and continue")
        self.ok_button.clicked.connect(self._on_ok_clicked)

        self._exit_button = QtWidgets.QPushButton("Exit")
        self._exit_button.setStyleSheet(
            ("color: rgb(64, 64, 64);"
             "background-color: rgb(128, 128, 128);"
             "padding: 0.5em;")
        )
        self._exit_button.setMinimumSize(64, 24)
        self._exit_button.setToolTip("Exit without saving")
        self._exit_button.clicked.connect(self._on_exit_clicked)

        bottom_layout.setContentsMargins(0, 10, 0, 0)
        bottom_layout.addWidget(pype_logo_label)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self.ok_button)
        bottom_layout.addWidget(self._exit_button)

        bottom_widget.setLayout(bottom_layout)
        bottom_widget.setStyleSheet("background-color: rgb(32, 32, 32);")

        # Console label
        # --------------------------------------------------------------------
        self._status_label = QtWidgets.QLabel("Console:")
        self._status_label.setContentsMargins(0, 10, 0, 10)
        self._status_label.setStyleSheet("color: rgb(61, 115, 97);")

        # Console
        # --------------------------------------------------------------------
        self._status_box = QtWidgets.QPlainTextEdit()
        self._status_box.setReadOnly(True)
        self._status_box.setCurrentCharFormat(self.default_console_style)
        self._status_box.setStyleSheet(
            """QPlainTextEdit {
                background-color: rgb(32, 32, 32);
                color: rgb(72, 200, 150);
                font-family: "Roboto Mono";
                font-size: 0.5em;
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
        self._progress_bar = QtWidgets.QProgressBar()
        self._progress_bar.setValue(0)
        self._progress_bar.setAlignment(QtCore.Qt.AlignCenter)
        self._progress_bar.setTextVisible(False)
        # setting font and the size
        self._progress_bar.setFont(QtGui.QFont('Arial', 7))
        self._progress_bar.setStyleSheet(
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
        main.addWidget(self.main_label)
        main.addWidget(self.pype_path_label)
        main.addLayout(input_layout)
        main.addWidget(self._mongo)
        main.addStretch(1)
        main.addWidget(self._status_label)
        main.addWidget(self._status_box)
        main.addWidget(self._progress_bar)
        main.addWidget(bottom_widget)
        self.setLayout(main)
        if not self.mongo_url:
            self._mongo.setVisible(False)
        else:
            if self._mongo.validate_url() and len(self.path) == 0:
                self._mongo.setVisible(True)
                self._mongo.setReadonly(True)

    def _on_select_clicked(self):
        """Show directory dialog."""
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        options |= QtWidgets.QFileDialog.ShowDirsOnly

        result = QtWidgets.QFileDialog.getExistingDirectory(
            parent=self,
            caption='Select path',
            directory=os.getcwd(),
            options=options)

        if not result:
            return

        filename = QtCore.QDir.toNativeSeparators(result)

        if os.path.isdir(filename):
            self.user_input.setText(filename)

    def _on_ok_clicked(self):
        """Start install process.

        This will once again validate entered path and if ok, start
        working thread that will do actual job.
        """
        valid, reason = validate_path_string(self.path)
        if not valid:
            self.user_input.setStyleSheet(
                """
                background-color: rgb(32, 19, 19);
                color: rgb(255, 69, 0);
                padding: 0.5em;
                border: 1px solid rgb(32, 64, 32);
                """
            )
            self.update_console(reason, True)
            return
        else:
            self.user_input.setStyleSheet(
                """
                background-color: rgb(19, 19, 19);
                color: rgb(64, 230, 132);
                padding: 0.5em;
                border: 1px solid rgb(32, 64, 32);
                """
            )
        if not self.path or not self.path.startswith("mongodb"):
            valid, reason = validate_mongo_connection(
                self._mongo.get_mongo_url()
            )
            if not valid:
                self._mongo.set_invalid()
                self.update_console(f"!!! {reason}", True)
                return
            else:
                self._mongo.set_valid()

        self._disable_buttons()
        self._install_thread = InstallThread(self)
        self._install_thread.message.connect(self.update_console)
        self._install_thread.progress.connect(self._update_progress)
        self._install_thread.finished.connect(self._enable_buttons)
        self._install_thread.set_path(self.path)
        self._install_thread.set_mongo(self._mongo.get_mongo_url())
        self._install_thread.start()

    def _update_progress(self, progress: int):
        self._progress_bar.setValue(progress)

    def _on_exit_clicked(self):
        self.close()

    def _path_changed(self, path: str) -> str:
        """Set path."""
        self.path = path
        if not self.path.startswith("mongodb"):
            self._mongo.setVisible(True)
        else:
            self._mongo.setVisible(False)

        if len(self.path) < 1 and not self.mongo_url:
            self._mongo.setVisible(False)

        if len(self.path) == 0 and self._mongo.validate_url():
            self._mongo.setVisible(True)
            self._mongo.set_read_only(True)
        else:
            self._mongo.set_read_only(False)
        return path

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
        self._btn_select.setEnabled(False)
        self._exit_button.setEnabled(False)
        self.ok_button.setEnabled(False)
        self._controls_disabled = True

    def _enable_buttons(self):
        """Enable buttons after operation is complete."""
        self._btn_select.setEnabled(True)
        self._exit_button.setEnabled(True)
        self.ok_button.setEnabled(True)
        self._controls_disabled = False

    def closeEvent(self, event):  # noqa
        """Prevent closing if window when controls are disabled."""
        if self._controls_disabled:
            return event.ignore()
        return super(InstallDialog, self).closeEvent(event)


class PathValidator(QValidator):
    """Validate mongodb url for Qt widgets."""

    def __init__(self, parent=None, intermediate=False):
        self.parent = parent
        self.intermediate = intermediate
        super(PathValidator, self).__init__(parent)

    def _return_state(
            self, state: QValidator.State, reason: str, path: str):
        """Set stylesheets and actions on parent based on state.

        Warning:
            This will always return `QFileDialog.State.Acceptable` as
            anything different will stop input to `QLineEdit`

        """

        if state == QValidator.State.Invalid:
            self.parent.setToolTip(reason)
            self.parent.setStyleSheet(
                """
                background-color: rgb(32, 19, 19);
                color: rgb(255, 69, 0);
                padding: 0.5em;
                border: 1px solid rgb(32, 64, 32);
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

        return QValidator.State.Acceptable, path, len(path)

    def validate(self, path: str, pos: int) -> (QValidator.State, str, int):  # noqa
        """Validate entered path.

        It can be regular path - in that case we test if it does exist.
        It can also be mongodb connection string. In that case we parse it
        as url (it should start with `mongodb://` url schema.

        Args:
            path (str): path, connection string url or pype token.
            pos (int): current position.

        Todo:
            It can also be Pype token, binding it to Pype user account.

        """
        if path.startswith("mongodb"):
            return self._return_state(
                QValidator.State.Intermediate, "", path)

        if len(path) < 6:
            return self._return_state(
                QValidator.State.Intermediate, "", path)

        valid, reason = validate_path_string(path)
        if not valid:
            return self._return_state(
                QValidator.State.Invalid, reason, path)
        else:
            return self._return_state(
                QValidator.State.Acceptable, reason, path)


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
        con_anim.setEndValue(32)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    d = InstallDialog()
    d.show()
    sys.exit(app.exec_())
