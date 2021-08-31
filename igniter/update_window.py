# -*- coding: utf-8 -*-
"""Progress window to show when OpenPype is updating/installing locally."""
import os
from .update_thread import UpdateThread
from Qt import QtCore, QtGui, QtWidgets  # noqa
from .bootstrap_repos import OpenPypeVersion
from .nice_progress_bar import NiceProgressBar
from .tools import load_stylesheet


class UpdateWindow(QtWidgets.QDialog):
    """OpenPype update window."""

    _width = 500
    _height = 100

    def __init__(self, version: OpenPypeVersion, parent=None):
        super(UpdateWindow, self).__init__(parent)
        self._openpype_version = version
        self._result_version_path = None

        self.setWindowTitle(
            f"OpenPype is updating ..."
        )
        self.setModal(True)
        self.setWindowFlags(
            QtCore.Qt.WindowMinimizeButtonHint
        )

        current_dir = os.path.dirname(os.path.abspath(__file__))
        roboto_font_path = os.path.join(current_dir, "RobotoMono-Regular.ttf")
        poppins_font_path = os.path.join(current_dir, "Poppins")
        icon_path = os.path.join(current_dir, "openpype_icon.png")

        # Install roboto font
        QtGui.QFontDatabase.addApplicationFont(roboto_font_path)
        for filename in os.listdir(poppins_font_path):
            if os.path.splitext(filename)[1] == ".ttf":
                QtGui.QFontDatabase.addApplicationFont(filename)

        # Load logo
        pixmap_openpype_logo = QtGui.QPixmap(icon_path)
        # Set logo as icon of window
        self.setWindowIcon(QtGui.QIcon(pixmap_openpype_logo))

        self._pixmap_openpype_logo = pixmap_openpype_logo

        self._update_thread = None

        self.resize(QtCore.QSize(self._width, self._height))
        self._init_ui()

        # Set stylesheet
        self.setStyleSheet(load_stylesheet())
        self._run_update()

    def _init_ui(self):

        # Main info
        # --------------------------------------------------------------------
        main_label = QtWidgets.QLabel(
            f"<b>OpenPype</b> is updating to {self._openpype_version}", self)
        main_label.setWordWrap(True)
        main_label.setObjectName("MainLabel")

        # Progress bar
        # --------------------------------------------------------------------
        progress_bar = NiceProgressBar(self)
        progress_bar.setAlignment(QtCore.Qt.AlignCenter)
        progress_bar.setTextVisible(False)

        # add all to main
        main = QtWidgets.QVBoxLayout(self)
        main.addSpacing(15)
        main.addWidget(main_label, 0)
        main.addSpacing(15)
        main.addWidget(progress_bar, 0)
        main.addSpacing(15)

        self._progress_bar = progress_bar

    def _run_update(self):
        """Start install process.

        This will once again validate entered path and mongo if ok, start
        working thread that will do actual job.
        """
        # Check if install thread is not already running
        if self._update_thread and self._update_thread.isRunning():
            return
        self._progress_bar.setRange(0, 0)
        update_thread = UpdateThread(self)
        update_thread.set_version(self._openpype_version)
        update_thread.message.connect(self.update_console)
        update_thread.progress.connect(self._update_progress)
        update_thread.finished.connect(self._installation_finished)

        self._update_thread = update_thread

        update_thread.start()

    def get_version_path(self):
        return self._result_version_path

    def _installation_finished(self):
        status = self._update_thread.result()
        self._result_version_path = status
        self._progress_bar.setRange(0, 1)
        self._update_progress(100)
        QtWidgets.QApplication.processEvents()
        self.done(0)

    def _update_progress(self, progress: int):
        # not updating progress as we are not able to determine it
        # correctly now. Progress bar is set to un-deterministic mode
        # until we are able to get progress in better way.
        """
        self._progress_bar.setRange(0, 0)
        self._progress_bar.setValue(progress)
        text_visible = self._progress_bar.isTextVisible()
        if progress == 0:
            if text_visible:
                self._progress_bar.setTextVisible(False)
        elif not text_visible:
            self._progress_bar.setTextVisible(True)
        """
        return

    def update_console(self, msg: str, error: bool = False) -> None:
        """Display message in console.

        Args:
            msg (str): message.
            error (bool): if True, print it red.
        """
        print(msg)
