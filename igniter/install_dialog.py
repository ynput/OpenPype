# -*- coding: utf-8 -*-
"""Show dialog for choosing central pype repository."""
import sys
import os
from Qt import QtCore, QtGui, QtWidgets


class InstallDialog(QtWidgets.QDialog):
    _size_w = 400
    _size_h = 300
    _path = None

    def __init__(self, parent=None):
        super(InstallDialog, self).__init__(parent)

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
            QtCore.QSize(self._size_w + 100, self._size_h + 100))

        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("background-color: rgb(23, 23, 23);")
        main = QtWidgets.QVBoxLayout(self)

        # Main info
        # --------------------------------------------------------------------
        self.main_label = QtWidgets.QLabel(
            """Welcome to <b>Pype</b>
            <p>
            We've detected <b>Pype</b> is not configured yet. But don't worry,
            this is as easy as setting one path.
            <p>
            """)
        self.main_label.setWordWrap(True)
        self.main_label.setStyleSheet("color: rgb(200, 200, 200);")

        # Pype path info
        # --------------------------------------------------------------------

        self.pype_path_label = QtWidgets.QLabel(
            """Set this path to your studio <b>Pype repository</b> to keep in
            sync with your studio environment. This can be path or url.
            Leave it empty if you want to use Pype version that come with this
            installation.
            """
        )

        self.pype_path_label.setWordWrap(True)
        self.pype_path_label.setStyleSheet("color: rgb(150, 150, 150);")

        # Path/Url box | Select button
        # --------------------------------------------------------------------

        input_layout = QtWidgets.QHBoxLayout()

        input_layout.setContentsMargins(0, 10, 0, 10)
        self.user_input = QtWidgets.QLineEdit()

        self.user_input.setPlaceholderText("Pype repository path or url")
        self.user_input.textChanged.connect(self._path_changed)
        self.user_input.setStyleSheet(
            ("color: rgb(233, 233, 233);"
             "background-color: rgb(64, 64, 64);"
             "padding: 0.5em;"
             "border: 1px solid rgb(32, 32, 32);")
        )

        self.btn_select = QtWidgets.QPushButton("Select")
        self.btn_select.setToolTip(
            "Select Pype repository"
        )
        self.btn_select.setStyleSheet(
            ("color: rgb(64, 64, 64);"
             "background-color: rgb(72, 200, 150);"
             "padding: 0.5em;")
        )
        self.btn_select.setMaximumSize(100, 140)
        self.btn_select.clicked.connect(self._on_select_clicked)

        input_layout.addWidget(self.user_input)
        input_layout.addWidget(self.btn_select)

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

        ok_button = QtWidgets.QPushButton("OK")
        ok_button.setStyleSheet(
            ("color: rgb(64, 64, 64);"
             "background-color: rgb(72, 200, 150);"
             "padding: 0.5em;")
        )
        ok_button.setMinimumSize(64, 24)
        ok_button.setToolTip("Save and continue")
        ok_button.clicked.connect(self._on_ok_clicked)

        exit_button = QtWidgets.QPushButton("Exit")
        exit_button.setStyleSheet(
            ("color: rgb(64, 64, 64);"
             "background-color: rgb(128, 128, 128);"
             "padding: 0.5em;")
        )
        exit_button.setMinimumSize(64, 24)
        exit_button.setToolTip("Exit without saving")
        exit_button.clicked.connect(self._on_exit_clicked)

        bottom_layout.setContentsMargins(0, 10, 0, 0)
        bottom_layout.addWidget(pype_logo_label)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(ok_button)
        bottom_layout.addWidget(exit_button)

        bottom_widget.setLayout(bottom_layout)
        bottom_widget.setStyleSheet("background-color: rgb(32, 32, 32);")

        # Status label
        # --------------------------------------------------------------------
        self._status_label = QtWidgets.QLabel()
        self._status_label.setContentsMargins(0, 10, 0, 10)
        self._status_label.setStyleSheet("color: rgb(72, 200, 150);")

        # add all to main

        main.addWidget(self.main_label)
        main.addWidget(self.pype_path_label)
        main.addLayout(input_layout)
        main.addStretch(1)
        main.addWidget(self._status_label)
        main.addWidget(bottom_widget)
        self.setLayout(main)

    def _on_select_clicked(self):
        fname = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Select path')

        if fname:
            fname = QtCore.QDir.toNativeSeparators(fname)

        if os.path.isdir(fname):
            self.user_input.setText(fname)

    def _on_ok_clicked(self):
        if not self._path:
            pass

    def _on_exit_clicked(self):
        self.close()

    def _path_changed(self, path):
        self._path = path
        self._status_label.setText(f"selected <b>{path}</b>")


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    d = InstallDialog()
    d.show()
    sys.exit(app.exec_())
