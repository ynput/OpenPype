import os
import logging
from functools import partial

from capture_gui.vendor.Qt import QtCore, QtWidgets
from capture_gui import plugin, lib
from capture_gui import tokens

log = logging.getLogger("IO")


class IoAction(QtWidgets.QAction):

    def __init__(self, parent, filepath):
        super(IoAction, self).__init__(parent)

        action_label = os.path.basename(filepath)

        self.setText(action_label)
        self.setData(filepath)

        # check if file exists and disable when false
        self.setEnabled(os.path.isfile(filepath))

        # get icon from file
        info = QtCore.QFileInfo(filepath)
        icon_provider = QtWidgets.QFileIconProvider()
        self.setIcon(icon_provider.icon(info))

        self.triggered.connect(self.open_object_data)

    def open_object_data(self):
        lib.open_file(self.data())


class IoPlugin(plugin.Plugin):
    """Codec widget.

    Allows to set format, compression and quality.

    """
    id = "IO"
    label = "Save"
    section = "app"
    order = 40
    max_recent_playblasts = 5

    def __init__(self, parent=None):
        super(IoPlugin, self).__init__(parent=parent)

        self.recent_playblasts = list()

        self._layout = QtWidgets.QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._layout)

        # region Checkboxes
        self.save_file = QtWidgets.QCheckBox(text="Save")
        self.open_viewer = QtWidgets.QCheckBox(text="View when finished")
        self.raw_frame_numbers = QtWidgets.QCheckBox(text="Raw frame numbers")

        checkbox_hlayout = QtWidgets.QHBoxLayout()
        checkbox_hlayout.setContentsMargins(5, 0, 5, 0)
        checkbox_hlayout.addWidget(self.save_file)
        checkbox_hlayout.addWidget(self.open_viewer)
        checkbox_hlayout.addWidget(self.raw_frame_numbers)
        checkbox_hlayout.addStretch(True)
        # endregion Checkboxes

        # region Path
        self.path_widget = QtWidgets.QWidget()

        self.browse = QtWidgets.QPushButton("Browse")
        self.file_path = QtWidgets.QLineEdit()
        self.file_path.setPlaceholderText("(not set; using scene name)")
        tip = "Right click in the text field to insert tokens"
        self.file_path.setToolTip(tip)
        self.file_path.setStatusTip(tip)
        self.file_path.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.file_path.customContextMenuRequested.connect(self.show_token_menu)

        path_hlayout = QtWidgets.QHBoxLayout()
        path_hlayout.setContentsMargins(0, 0, 0, 0)
        path_label = QtWidgets.QLabel("Path:")
        path_label.setFixedWidth(30)

        path_hlayout.addWidget(path_label)
        path_hlayout.addWidget(self.file_path)
        path_hlayout.addWidget(self.browse)
        self.path_widget.setLayout(path_hlayout)
        # endregion Path

        # region Recent Playblast
        self.play_recent = QtWidgets.QPushButton("Play recent playblast")
        self.recent_menu = QtWidgets.QMenu()
        self.play_recent.setMenu(self.recent_menu)
        # endregion Recent Playblast

        self._layout.addLayout(checkbox_hlayout)
        self._layout.addWidget(self.path_widget)
        self._layout.addWidget(self.play_recent)

        # Signals  / connections
        self.browse.clicked.connect(self.show_browse_dialog)
        self.file_path.textChanged.connect(self.options_changed)
        self.save_file.stateChanged.connect(self.options_changed)
        self.raw_frame_numbers.stateChanged.connect(self.options_changed)
        self.save_file.stateChanged.connect(self.on_save_changed)

        # Ensure state is up-to-date with current settings
        self.on_save_changed()

    def on_save_changed(self):
        """Update the visibility of the path field"""

        state = self.save_file.isChecked()
        if state:
            self.path_widget.show()
        else:
            self.path_widget.hide()

    def show_browse_dialog(self):
        """Set the filepath using a browser dialog.

        :return: None
        """

        path = lib.browse()
        if not path:
            return

        # Maya's browser return Linux based file paths to ensure Windows is
        # supported we use normpath
        path = os.path.normpath(path)

        self.file_path.setText(path)

    def add_playblast(self, item):
        """
        Add an item to the previous playblast menu

        :param item: full path to a playblast file
        :type item: str

        :return: None
        """

        # If item already in the recent playblasts remove it so we are
        # sure to add it as the new first most-recent
        try:
            self.recent_playblasts.remove(item)
        except ValueError:
            pass

        # Add as first in the recent playblasts
        self.recent_playblasts.insert(0, item)

        # Ensure the playblast list is never longer than maximum amount
        # by removing the older entries that are at the end of the list
        if len(self.recent_playblasts) > self.max_recent_playblasts:
            del self.recent_playblasts[self.max_recent_playblasts:]

        # Rebuild the actions menu
        self.recent_menu.clear()
        for playblast in self.recent_playblasts:
            action = IoAction(parent=self, filepath=playblast)
            self.recent_menu.addAction(action)

    def on_playblast_finished(self, options):
        """Take action after the play blast is done"""
        playblast_file = options['filename']
        if not playblast_file:
            return
        self.add_playblast(playblast_file)

    def get_outputs(self):
        """Get the plugin outputs that matches `capture.capture` arguments

        Returns:
            dict: Plugin outputs

        """

        output = {"filename": None,
                  "raw_frame_numbers": self.raw_frame_numbers.isChecked(),
                  "viewer": self.open_viewer.isChecked()}

        save = self.save_file.isChecked()
        if not save:
            return output

        # get path, if nothing is set fall back to default
        # project/images/playblast
        path = self.file_path.text()
        if not path:
            path = lib.default_output()

        output["filename"] = path

        return output

    def get_inputs(self, as_preset):
        inputs = {"name": self.file_path.text(),
                  "save_file": self.save_file.isChecked(),
                  "open_finished": self.open_viewer.isChecked(),
                  "recent_playblasts": self.recent_playblasts,
                  "raw_frame_numbers": self.raw_frame_numbers.isChecked()}

        if as_preset:
            inputs["recent_playblasts"] = []

        return inputs

    def apply_inputs(self, settings):

        directory = settings.get("name", None)
        save_file = settings.get("save_file", True)
        open_finished = settings.get("open_finished", True)
        raw_frame_numbers = settings.get("raw_frame_numbers", False)
        previous_playblasts = settings.get("recent_playblasts", [])

        self.save_file.setChecked(save_file)
        self.open_viewer.setChecked(open_finished)
        self.raw_frame_numbers.setChecked(raw_frame_numbers)

        for playblast in reversed(previous_playblasts):
            self.add_playblast(playblast)

        self.file_path.setText(directory)

    def token_menu(self):
        """
        Build the token menu based on the registered tokens

        :returns: Menu
        :rtype: QtWidgets.QMenu
        """
        menu = QtWidgets.QMenu(self)
        registered_tokens = tokens.list_tokens()

        for token, value in registered_tokens.items():
            label = "{} \t{}".format(token, value['label'])
            action = QtWidgets.QAction(label, menu)
            fn = partial(self.file_path.insert, token)
            action.triggered.connect(fn)
            menu.addAction(action)

        return menu

    def show_token_menu(self, pos):
        """Show custom manu on position of widget"""
        menu = self.token_menu()
        globalpos = QtCore.QPoint(self.file_path.mapToGlobal(pos))
        menu.exec_(globalpos)
