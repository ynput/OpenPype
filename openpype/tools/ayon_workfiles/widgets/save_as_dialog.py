import os
import copy

from qtpy import QtWidgets, QtCore

from openpype.pipeline.workfile import get_last_workfile_with_version

from openpype.pipeline import get_current_host_name
from openpype.tools.utils import PlaceholderLineEdit


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
    """Save as dialog to define a unique filename inside workdir.

    The filename is calculated in controller where UI sends values from
    dialog inputs.

    Args:
        controller (AbstractWorkfilesFrontend): The control object.
    """

    def __init__(self, controller, parent):
        super(SaveAsDialog, self).__init__(parent=parent)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.FramelessWindowHint)

        self._controller = controller

        self._folder_id = None
        self._task_id = None
        self._last_version = None
        self._template_key = None
        self._comment_value = None
        self._version_value = None
        self._ext_value = None
        self._filename = None
        self._workdir = None

        self._result = None

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
        preview_widget = QtWidgets.QLabel("Preview filename", inputs_widget)
        preview_widget.setWordWrap(True)

        # Subversion input
        subversion_input = SubversionLineEdit(inputs_widget)
        subversion_input.set_placeholder("Will be part of filename.")

        # Extensions combobox
        extension_combobox = QtWidgets.QComboBox(inputs_widget)
        # Add styled delegate to use stylesheets
        extension_delegate = QtWidgets.QStyledItemDelegate()
        extension_combobox.setItemDelegate(extension_delegate)

        version_label = QtWidgets.QLabel("Version:", inputs_widget)
        subversion_label = QtWidgets.QLabel("Subversion:", inputs_widget)
        extension_label = QtWidgets.QLabel("Extension:", inputs_widget)
        preview_label = QtWidgets.QLabel("Preview:", inputs_widget)

        # Build inputs
        inputs_layout = QtWidgets.QGridLayout(inputs_widget)
        inputs_layout.addWidget(version_label, 0, 0)
        inputs_layout.addWidget(version_widget, 0, 1)
        inputs_layout.addWidget(subversion_label, 1, 0)
        inputs_layout.addWidget(subversion_input, 1, 1)
        inputs_layout.addWidget(extension_label, 2, 0)
        inputs_layout.addWidget(extension_combobox, 2, 1)
        inputs_layout.addWidget(preview_label, 3, 0)
        inputs_layout.addWidget(preview_widget, 3, 1)

        # Build layout
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(inputs_widget)
        main_layout.addWidget(btns_widget)

        # Signal callback registration
        version_input.valueChanged.connect(self._on_version_spinbox_change)
        last_version_check.stateChanged.connect(
            self._on_version_checkbox_change
        )

        subversion_input.text_changed.connect(self._on_comment_change)
        extension_combobox.currentIndexChanged.connect(
            self._on_extension_change)

        btn_ok.pressed.connect(self._on_ok_pressed)
        btn_cancel.pressed.connect(self._on_cancel_pressed)

        # Store objects
        self._inputs_layout = inputs_layout

        self._btn_ok = btn_ok
        self._btn_cancel = btn_cancel

        self._version_widget = version_widget

        self._version_input = version_input
        self._last_version_check = last_version_check

        self._extension_delegate = extension_delegate
        self._extension_combobox = extension_combobox
        self._subversion_input = subversion_input
        self._preview_widget = preview_widget

        self._version_label = version_label
        self._subversion_label = subversion_label
        self._extension_label = extension_label
        self._preview_label = preview_label

        # Post init setup

        # Allow "Enter" key to accept the save.
        btn_ok.setDefault(True)

        # Disable version input if last version is checked
        version_input.setEnabled(not last_version_check.isChecked())

        # Force default focus to comment, some hosts didn't automatically
        # apply focus to this line edit (e.g. Houdini)
        subversion_input.setFocus()

    def get_result(self):
        return self._result

    def update_context(self):
        # Add version only if template contains version key
        # - since the version can be padded with "{version:0>4}" we only search
        #   for "{version".
        selected_context = self._controller.get_selected_context()
        folder_id = selected_context["folder_id"]
        task_id = selected_context["task_id"]
        data = self._controller.get_workarea_save_as_data(folder_id, task_id)
        last_version = data["last_version"]
        comment = data["comment"]
        comment_hints = data["comment_hints"]

        template_has_version = data["template_has_version"]
        template_has_comment = data["template_has_comment"]

        self._folder_id = folder_id
        self._task_id = task_id
        self._workdir = data["workdir"]
        self._comment_value = data["comment"]
        self._ext_value = data["ext"]
        self._template_key = data["template_key"]
        self._last_version = data["last_version"]

        self._extension_combobox.clear()
        self._extension_combobox.addItems(data["extensions"])

        self._version_input.setValue(last_version)

        vw_idx = self._inputs_layout.indexOf(self._version_widget)
        self._version_label.setVisible(template_has_version)
        self._version_widget.setVisible(template_has_version)
        if template_has_version:
            if vw_idx == -1:
                self._inputs_layout.addWidget(self._version_label, 0, 0)
                self._inputs_layout.addWidget(self._version_widget, 0, 1)
        elif vw_idx != -1:
            self._inputs_layout.takeAt(vw_idx)
            self._inputs_layout.takeAt(
                self._inputs_layout.indexOf(self._version_label)
            )

        cw_idx = self._inputs_layout.indexOf(self._subversion_input)
        self._subversion_label.setVisible(template_has_comment)
        self._subversion_input.setVisible(template_has_comment)
        if template_has_comment:
            if cw_idx == -1:
                self._inputs_layout.addWidget(self._subversion_label, 1, 0)
                self._inputs_layout.addWidget(self._subversion_input, 1, 1)
        elif cw_idx != -1:
            self._inputs_layout.takeAt(cw_idx)
            self._inputs_layout.takeAt(
                self._inputs_layout.indexOf(self._subversion_label)
            )

        if template_has_comment:
            self._subversion_input.set_text(comment or "")
            self._subversion_input.set_values(comment_hints)
        self._update_filename()

    def _on_version_spinbox_change(self, value):
        if value == self._version_value:
            return
        self._version_value = value
        if not self._last_version_check.isChecked():
            self._update_filename()

    def _on_version_checkbox_change(self):
        use_last_version = self._last_version_check.isChecked()
        self._version_input.setEnabled(not use_last_version)
        if use_last_version:
            self._version_input.blockSignals(True)
            self._version_input.setValue(self._last_version)
            self._version_input.blockSignals(False)
        self._update_filename()

    def _on_comment_change(self, text):
        if self._comment_value == text:
            return
        self._comment_value = text
        self._update_filename()

    def _on_extension_change(self):
        ext = self._extension_combobox.currentText()
        if ext == self._ext_value:
            return
        self._ext_value = ext
        self._update_filename()

    def _on_ok_pressed(self):
        self._result = {
            "filename": self._filename,
            "workdir": self._workdir,
            "folder_id": self._folder_id,
            "task_id": self._task_id,
            "template_key": self._template_key,
        }
        self.close()

    def _on_cancel_pressed(self):
        self.close()

    def _update_filename(self):
        result = self._controller.fill_workarea_filepath(
            self._folder_id,
            self._task_id,
            self._ext_value,
            self._last_version_check.isChecked(),
            self._version_value,
            self._comment_value,
        )
        self._filename = result.filename
        self._btn_ok.setEnabled(not result.exists)

        if result.exists:
            self._preview_widget.setText((
                "<font color='red'>Cannot create \"{}\" because file exists!"
                "</font>"
            ).format(result.filename))
        else:
            self._preview_widget.setText(
                "<font color='green'>{}</font>".format(result.filename)
            )
