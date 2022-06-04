import os
import re
import copy
import logging

from Qt import QtWidgets, QtCore

from openpype.client import (
    get_project,
    get_asset,
)
from openpype.lib import (
    get_last_workfile_with_version,
    get_workdir_data,
)
from openpype.pipeline import (
    registered_host,
    legacy_io,
)
from openpype.tools.utils import PlaceholderLineEdit

log = logging.getLogger(__name__)


def build_workfile_data(session):
    """Get the data required for workfile formatting from avalon `session`"""

    # Set work file data for template formatting
    project_name = session["AVALON_PROJECT"]
    asset_name = session["AVALON_ASSET"]
    task_name = session["AVALON_TASK"]
    host_name = session["AVALON_APP"]
    project_doc = get_project(
        project_name, fields=["name", "data.code", "config.tasks"]
    )
    asset_doc = get_asset(
        project_name,
        asset_name=asset_name,
        fields=["name", "data.tasks", "data.parents"]
    )

    data = get_workdir_data(project_doc, asset_doc, task_name, host_name)
    data.update({
        "version": 1,
        "comment": "",
        "ext": None
    })

    return data


class CommentMatcher(object):
    """Use anatomy and work file data to parse comments from filenames"""
    def __init__(self, anatomy, template_key, data):

        self.fname_regex = None

        template = anatomy.templates[template_key]["file"]
        if "{comment}" not in template:
            # Don't look for comment if template doesn't allow it
            return

        # Create a regex group for extensions
        extensions = registered_host().file_extensions()
        any_extension = "(?:{})".format(
            "|".join(re.escape(ext[1:]) for ext in extensions)
        )

        # Use placeholders that will never be in the filename
        temp_data = copy.deepcopy(data)
        temp_data["comment"] = "<<comment>>"
        temp_data["version"] = "<<version>>"
        temp_data["ext"] = "<<ext>>"

        formatted = anatomy.format(temp_data)
        fname_pattern = formatted[template_key]["file"]
        fname_pattern = re.escape(fname_pattern)

        # Replace comment and version with something we can match with regex
        replacements = {
            "<<comment>>": "(.+)",
            "<<version>>": "[0-9]+",
            "<<ext>>": any_extension,
        }
        for src, dest in replacements.items():
            fname_pattern = fname_pattern.replace(re.escape(src), dest)

        # Match from beginning to end of string to be safe
        fname_pattern = "^{}$".format(fname_pattern)

        self.fname_regex = re.compile(fname_pattern)

    def parse_comment(self, filepath):
        """Parse the {comment} part from a filename"""
        if not self.fname_regex:
            return

        fname = os.path.basename(filepath)
        match = self.fname_regex.match(fname)
        if match:
            return match.group(1)


class SubversionLineEdit(QtWidgets.QWidget):
    """QLineEdit with QPushButton for drop down selection of list of strings"""

    text_changed = QtCore.Signal(str)

    def __init__(self, *args, **kwargs):
        super(SubversionLineEdit, self).__init__(*args, **kwargs)

        input_field = PlaceholderLineEdit(self)
        menu_btn = QtWidgets.QPushButton(self)
        menu_btn.setFixedWidth(18)

        menu = QtWidgets.QMenu(self)
        menu_btn.setMenu(menu)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)

        layout.addWidget(input_field, 1)
        layout.addWidget(menu_btn, 0)

        input_field.textChanged.connect(self.text_changed)

        self.setFocusProxy(input_field)

        self._input_field = input_field
        self._menu_btn = menu_btn
        self._menu = menu

    def set_placeholder(self, placeholder):
        self._input_field.setPlaceholderText(placeholder)

    def set_text(self, text):
        self._input_field.setText(text)

    def set_values(self, values):
        self._update(values)

    def _on_button_clicked(self):
        self._menu.exec_()

    def _on_action_clicked(self, action):
        self._input_field.setText(action.text())

    def _update(self, values):
        """Create optional predefined subset names

        Args:
            default_names(list): all predefined names

        Returns:
             None
        """

        menu = self._menu
        button = self._menu_btn

        state = any(values)
        button.setEnabled(state)
        if state is False:
            return

        # Include an empty string
        values = [""] + sorted(values)

        # Get and destroy the action group
        group = button.findChild(QtWidgets.QActionGroup)
        if group:
            group.deleteLater()

        # Build new action group
        group = QtWidgets.QActionGroup(button)
        for name in values:
            action = group.addAction(name)
            menu.addAction(action)

        group.triggered.connect(self._on_action_clicked)


class SaveAsDialog(QtWidgets.QDialog):
    """Name Window to define a unique filename inside a root folder

    The filename will be based on the "workfile" template defined in the
    project["config"]["template"].

    """

    def __init__(
        self, parent, root, anatomy, template_key, extensions, session=None
    ):
        super(SaveAsDialog, self).__init__(parent=parent)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint)

        self.result = None
        self.host = registered_host()
        self.root = root
        self.work_file = None
        self._extensions = extensions

        if not session:
            # Fallback to active session
            session = legacy_io.Session

        self.data = build_workfile_data(session)

        # Store project anatomy
        self.anatomy = anatomy
        self.template = anatomy.templates[template_key]["file"]
        self.template_key = template_key

        # Btns widget
        btns_widget = QtWidgets.QWidget(self)

        btn_ok = QtWidgets.QPushButton("Ok", btns_widget)
        btn_cancel = QtWidgets.QPushButton("Cancel", btns_widget)

        btns_layout = QtWidgets.QHBoxLayout(btns_widget)
        btns_layout.addWidget(btn_ok)
        btns_layout.addWidget(btn_cancel)

        # Inputs widget
        inputs_widget = QtWidgets.QWidget(self)

        # Version widget
        version_widget = QtWidgets.QWidget(inputs_widget)

        # Version number input
        version_input = QtWidgets.QSpinBox(version_widget)
        version_input.setMinimum(1)
        version_input.setMaximum(9999)

        # Last version checkbox
        last_version_check = QtWidgets.QCheckBox(
            "Next Available Version", version_widget
        )
        last_version_check.setChecked(True)

        version_layout = QtWidgets.QHBoxLayout(version_widget)
        version_layout.setContentsMargins(0, 0, 0, 0)
        version_layout.addWidget(version_input)
        version_layout.addWidget(last_version_check)

        # Preview widget
        preview_label = QtWidgets.QLabel("Preview filename", inputs_widget)

        # Subversion input
        subversion = SubversionLineEdit(inputs_widget)
        subversion.set_placeholder("Will be part of filename.")

        # Extensions combobox
        ext_combo = QtWidgets.QComboBox(inputs_widget)
        # Add styled delegate to use stylesheets
        ext_delegate = QtWidgets.QStyledItemDelegate()
        ext_combo.setItemDelegate(ext_delegate)
        ext_combo.addItems(self._extensions)

        # Build inputs
        inputs_layout = QtWidgets.QFormLayout(inputs_widget)
        # Add version only if template contains version key
        # - since the version can be padded with "{version:0>4}" we only search
        #   for "{version".
        if "{version" in self.template:
            inputs_layout.addRow("Version:", version_widget)
        else:
            version_widget.setVisible(False)

        # Add subversion only if template contains `{comment}`
        if "{comment}" in self.template:
            inputs_layout.addRow("Subversion:", subversion)

            # Detect whether a {comment} is in the current filename - if so,
            # preserve it by default and set it in the comment/subversion field
            current_filepath = self.host.current_file()
            if current_filepath:
                # We match the current filename against the current session
                # instead of the session where the user is saving to.
                current_data = build_workfile_data(legacy_io.Session)
                matcher = CommentMatcher(anatomy, template_key, current_data)
                comment = matcher.parse_comment(current_filepath)
                if comment:
                    log.info("Detected subversion comment: {}".format(comment))
                    self.data["comment"] = comment
                    subversion.set_text(comment)

            existing_comments = self.get_existing_comments()
            subversion.set_values(existing_comments)

        else:
            subversion.setVisible(False)
        inputs_layout.addRow("Extension:", ext_combo)
        inputs_layout.addRow("Preview:", preview_label)

        # Build layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(inputs_widget)
        main_layout.addWidget(btns_widget)

        # Signal callback registration
        version_input.valueChanged.connect(self.on_version_spinbox_changed)
        last_version_check.stateChanged.connect(
            self.on_version_checkbox_changed
        )

        subversion.text_changed.connect(self.on_comment_changed)
        ext_combo.currentIndexChanged.connect(self.on_extension_changed)

        btn_ok.pressed.connect(self.on_ok_pressed)
        btn_cancel.pressed.connect(self.on_cancel_pressed)

        # Allow "Enter" key to accept the save.
        btn_ok.setDefault(True)

        # Force default focus to comment, some hosts didn't automatically
        # apply focus to this line edit (e.g. Houdini)
        subversion.setFocus()

        # Store widgets
        self.btn_ok = btn_ok

        self.version_widget = version_widget

        self.version_input = version_input
        self.last_version_check = last_version_check

        self.preview_label = preview_label
        self.subversion = subversion
        self.ext_combo = ext_combo
        self._ext_delegate = ext_delegate

        self.refresh()

    def get_existing_comments(self):
        matcher = CommentMatcher(self.anatomy, self.template_key, self.data)
        host_extensions = set(self._extensions)
        comments = set()
        if os.path.isdir(self.root):
            for fname in os.listdir(self.root):
                if not os.path.isfile(os.path.join(self.root, fname)):
                    continue

                ext = os.path.splitext(fname)[-1]
                if ext not in host_extensions:
                    continue

                comment = matcher.parse_comment(fname)
                if comment:
                    comments.add(comment)

        return list(comments)

    def on_version_spinbox_changed(self, value):
        self.data["version"] = value
        self.refresh()

    def on_version_checkbox_changed(self, _value):
        self.refresh()

    def on_comment_changed(self, text):
        self.data["comment"] = text
        self.refresh()

    def on_extension_changed(self):
        ext = self.ext_combo.currentText()
        if ext == self.data["ext"]:
            return
        self.data["ext"] = ext
        self.refresh()

    def on_ok_pressed(self):
        self.result = self.work_file
        self.close()

    def on_cancel_pressed(self):
        self.close()

    def get_result(self):
        return self.result

    def get_work_file(self):
        data = copy.deepcopy(self.data)
        if not data["comment"]:
            data.pop("comment", None)

        data["ext"] = data["ext"][1:]

        anatomy_filled = self.anatomy.format(data)
        return anatomy_filled[self.template_key]["file"]

    def refresh(self):
        extensions = list(self._extensions)
        extension = self.data["ext"]
        if extension is None:
            # Define saving file extension
            current_file = self.host.current_file()
            if current_file:
                # Match the extension of current file
                _, extension = os.path.splitext(current_file)
            else:
                extension = extensions[0]

        if extension != self.data["ext"]:
            self.data["ext"] = extension
            index = self.ext_combo.findText(
                extension, QtCore.Qt.MatchFixedString
            )
            if index >= 0:
                self.ext_combo.setCurrentIndex(index)

        if not self.last_version_check.isChecked():
            self.version_input.setEnabled(True)
            self.data["version"] = self.version_input.value()

            work_file = self.get_work_file()

        else:
            self.version_input.setEnabled(False)

            data = copy.deepcopy(self.data)
            template = str(self.template)

            if not data["comment"]:
                data.pop("comment", None)

            data["ext"] = data["ext"][1:]

            version = get_last_workfile_with_version(
                self.root, template, data, extensions
            )[1]

            if version is None:
                version = 1
            else:
                version += 1

            found_valid_version = False
            # Check if next version is valid version and give a chance to try
            # next 100 versions
            for idx in range(100):
                # Store version to data
                self.data["version"] = version

                work_file = self.get_work_file()
                # Safety check
                path = os.path.join(self.root, work_file)
                if not os.path.exists(path):
                    found_valid_version = True
                    break

                # Try next version
                version += 1
                # Log warning
                if idx == 0:
                    log.warning((
                        "BUG: Function `get_last_workfile_with_version` "
                        "didn't return last version."
                    ))
            # Raise exception if even 100 version fallback didn't help
            if not found_valid_version:
                raise AssertionError(
                    "This is a bug. Couldn't find valid version!"
                )

        self.work_file = work_file

        path_exists = os.path.exists(os.path.join(self.root, work_file))

        self.btn_ok.setEnabled(not path_exists)

        if path_exists:
            self.preview_label.setText(
                "<font color='red'>Cannot create \"{0}\" because file exists!"
                "</font>".format(work_file)
            )
        else:
            self.preview_label.setText(
                "<font color='green'>{0}</font>".format(work_file)
            )
