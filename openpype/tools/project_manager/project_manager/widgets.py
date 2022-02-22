import re

from .constants import (
    NAME_ALLOWED_SYMBOLS,
    NAME_REGEX
)
from openpype.lib import (
    create_project,
    PROJECT_NAME_ALLOWED_SYMBOLS,
    PROJECT_NAME_REGEX
)
from openpype.style import load_stylesheet
from openpype.tools.utils import (
    PlaceholderLineEdit,
    get_warning_pixmap
)
from avalon.api import AvalonMongoDB

from Qt import QtWidgets, QtCore, QtGui


class NameTextEdit(QtWidgets.QLineEdit):
    def __init__(self, *args, **kwargs):
        super(NameTextEdit, self).__init__(*args, **kwargs)

        self.textChanged.connect(self._on_text_change)

    def _on_text_change(self, text):
        if NAME_REGEX.match(text):
            return

        idx = self.cursorPosition()
        before_text = text[0:idx]
        after_text = text[idx:len(text)]
        sub_regex = "[^{}]+".format(NAME_ALLOWED_SYMBOLS)
        new_before_text = re.sub(sub_regex, "", before_text)
        new_after_text = re.sub(sub_regex, "", after_text)
        idx -= (len(before_text) - len(new_before_text))

        self.setText(new_before_text + new_after_text)
        self.setCursorPosition(idx)


class FilterComboBox(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(FilterComboBox, self).__init__(parent)

        self._last_value = None

        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setEditable(True)
        combobox_delegate = QtWidgets.QStyledItemDelegate(self)
        self.setItemDelegate(combobox_delegate)

        filter_proxy_model = QtCore.QSortFilterProxyModel(self)
        filter_proxy_model.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)
        filter_proxy_model.setSourceModel(self.model())

        completer = QtWidgets.QCompleter(filter_proxy_model, self)
        completer.setCompletionMode(
            QtWidgets.QCompleter.UnfilteredPopupCompletion
        )
        self.setCompleter(completer)

        completer_view = completer.popup()
        completer_view.setObjectName("CompleterView")
        delegate = QtWidgets.QStyledItemDelegate(completer_view)
        completer_view.setItemDelegate(delegate)
        completer_view.setStyleSheet(load_stylesheet())

        self.lineEdit().textEdited.connect(
            filter_proxy_model.setFilterFixedString
        )
        completer.activated.connect(self.on_completer_activated)

        self._completer = completer
        self._filter_proxy_model = filter_proxy_model

    def focusInEvent(self, event):
        super(FilterComboBox, self).focusInEvent(event)
        self._last_value = self.lineEdit().text()
        self.lineEdit().selectAll()

    def value_cleanup(self):
        text = self.lineEdit().text()
        idx = self.findText(text)
        if idx < 0:
            count = self._completer.completionModel().rowCount()
            if count > 0:
                index = self._completer.completionModel().index(0, 0)
                text = index.data(QtCore.Qt.DisplayRole)
                idx = self.findText(text)
            elif self._last_value is not None:
                idx = self.findText(self._last_value)

        if idx < 0:
            idx = 0
        self.setCurrentIndex(idx)

    def on_completer_activated(self, text):
        if text:
            index = self.findText(text)
            self.setCurrentIndex(index)

    def keyPressEvent(self, event):
        if event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            self.value_cleanup()

        super(FilterComboBox, self).keyPressEvent(event)

    def setModel(self, model):
        super(FilterComboBox, self).setModel(model)
        self._filter_proxy_model.setSourceModel(model)
        self._completer.setModel(self._filter_proxy_model)

    def setModelColumn(self, column):
        self._completer.setCompletionColumn(column)
        self._filter_proxy_model.setFilterKeyColumn(column)
        super(FilterComboBox, self).setModelColumn(column)


class CreateProjectDialog(QtWidgets.QDialog):
    def __init__(self, parent=None, dbcon=None):
        super(CreateProjectDialog, self).__init__(parent)

        self.setWindowTitle("Create Project")

        self.allowed_regex = "[^{}]+".format(PROJECT_NAME_ALLOWED_SYMBOLS)

        if dbcon is None:
            dbcon = AvalonMongoDB()

        self.dbcon = dbcon
        self._ignore_code_change = False
        self._project_name_is_valid = False
        self._project_code_is_valid = False
        self._project_code_value = None

        project_names, project_codes = self._get_existing_projects()

        inputs_widget = QtWidgets.QWidget(self)
        project_name_input = QtWidgets.QLineEdit(inputs_widget)
        project_code_input = QtWidgets.QLineEdit(inputs_widget)
        library_project_input = QtWidgets.QCheckBox(inputs_widget)

        inputs_layout = QtWidgets.QFormLayout(inputs_widget)
        inputs_layout.setContentsMargins(0, 0, 0, 0)
        inputs_layout.addRow("Project name:", project_name_input)
        inputs_layout.addRow("Project code:", project_code_input)
        inputs_layout.addRow("Library project:", library_project_input)

        project_name_label = QtWidgets.QLabel(self)
        project_code_label = QtWidgets.QLabel(self)

        btns_widget = QtWidgets.QWidget(self)
        ok_btn = QtWidgets.QPushButton("Ok", btns_widget)
        ok_btn.setEnabled(False)
        cancel_btn = QtWidgets.QPushButton("Cancel", btns_widget)
        btns_layout = QtWidgets.QHBoxLayout(btns_widget)
        btns_layout.setContentsMargins(0, 0, 0, 0)
        btns_layout.addStretch(1)
        btns_layout.addWidget(ok_btn)
        btns_layout.addWidget(cancel_btn)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(inputs_widget, 0)
        main_layout.addWidget(project_name_label, 1)
        main_layout.addWidget(project_code_label, 1)
        main_layout.addStretch(1)
        main_layout.addWidget(btns_widget, 0)

        project_name_input.textChanged.connect(self._on_project_name_change)
        project_code_input.textChanged.connect(self._on_project_code_change)
        ok_btn.clicked.connect(self._on_ok_clicked)
        cancel_btn.clicked.connect(self._on_cancel_clicked)

        self.invalid_project_names = project_names
        self.invalid_project_codes = project_codes

        self.project_name_label = project_name_label
        self.project_code_label = project_code_label

        self.project_name_input = project_name_input
        self.project_code_input = project_code_input
        self.library_project_input = library_project_input

        self.ok_btn = ok_btn

    @property
    def project_name(self):
        return self.project_name_input.text()

    def _on_project_name_change(self, value):
        if self._project_code_value is None:
            self._ignore_code_change = True
            self.project_code_input.setText(value.lower())
            self._ignore_code_change = False

        self._update_valid_project_name(value)

    def _on_project_code_change(self, value):
        if not value:
            value = None

        self._update_valid_project_code(value)

        if not self._ignore_code_change:
            self._project_code_value = value

    def _update_valid_project_name(self, value):
        message = ""
        is_valid = True
        if not value:
            message = "Project name is empty"
            is_valid = False

        elif value in self.invalid_project_names:
            message = "Project name \"{}\" already exist".format(value)
            is_valid = False

        elif not PROJECT_NAME_REGEX.match(value):
            message = (
                "Project name \"{}\" contain not supported symbols"
            ).format(value)
            is_valid = False

        self._project_name_is_valid = is_valid
        self.project_name_label.setText(message)
        self.project_name_label.setVisible(bool(message))
        self._enable_button()

    def _update_valid_project_code(self, value):
        message = ""
        is_valid = True
        if not value:
            message = "Project code is empty"
            is_valid = False

        elif value in self.invalid_project_names:
            message = "Project code \"{}\" already exist".format(value)
            is_valid = False

        elif not PROJECT_NAME_REGEX.match(value):
            message = (
                "Project code \"{}\" contain not supported symbols"
            ).format(value)
            is_valid = False

        self._project_code_is_valid = is_valid
        self.project_code_label.setText(message)
        self._enable_button()

    def _enable_button(self):
        self.ok_btn.setEnabled(
            self._project_name_is_valid and self._project_code_is_valid
        )

    def _on_cancel_clicked(self):
        self.done(0)

    def _on_ok_clicked(self):
        if not self._project_name_is_valid or not self._project_code_is_valid:
            return

        project_name = self.project_name_input.text()
        project_code = self.project_code_input.text()
        library_project = self.library_project_input.isChecked()
        create_project(project_name, project_code, library_project, self.dbcon)

        self.done(1)

    def _get_existing_projects(self):
        project_names = set()
        project_codes = set()
        for project_name in self.dbcon.database.collection_names():
            # Each collection will have exactly one project document
            project_doc = self.dbcon.database[project_name].find_one(
                {"type": "project"},
                {"name": 1, "data.code": 1}
            )
            if not project_doc:
                continue

            project_name = project_doc.get("name")
            if not project_name:
                continue

            project_names.add(project_name)
            project_code = project_doc.get("data", {}).get("code")
            if not project_code:
                project_code = project_name

            project_codes.add(project_code)
        return project_names, project_codes


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
        size = self.fontMetrics().height() * 4
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


class ConfirmProjectDeletion(QtWidgets.QDialog):
    """Dialog which confirms deletion of a project."""
    def __init__(self, project_name, parent):
        super(ConfirmProjectDeletion, self).__init__(parent)

        self.setWindowTitle("Delete project?")

        top_widget = QtWidgets.QWidget(self)

        warning_pixmap = get_warning_pixmap()
        warning_icon_label = PixmapLabel(warning_pixmap, top_widget)

        message_label = QtWidgets.QLabel(top_widget)
        message_label.setWordWrap(True)
        message_label.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        message_label.setText((
            "<b>WARNING: This cannot be undone.</b><br/><br/>"
            "Project <b>\"{}\"</b> with all related data will be"
            " permanently removed from the database. (This action won't remove"
            " any files on disk.)"
        ).format(project_name))

        top_layout = QtWidgets.QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addWidget(
            warning_icon_label, 0,
            QtCore.Qt.AlignTop | QtCore.Qt.AlignHCenter
        )
        top_layout.addWidget(message_label, 1)

        question_label = QtWidgets.QLabel("<b>Are you sure?</b>", self)

        confirm_input = PlaceholderLineEdit(self)
        confirm_input.setPlaceholderText(
            "Type \"{}\" to confirm...".format(project_name)
        )

        cancel_btn = QtWidgets.QPushButton("Cancel", self)
        cancel_btn.setToolTip("Cancel deletion of the project")
        confirm_btn = QtWidgets.QPushButton("Permanently Delete Project", self)
        confirm_btn.setObjectName("DeleteButton")
        confirm_btn.setEnabled(False)
        confirm_btn.setToolTip("Confirm deletion")

        btns_layout = QtWidgets.QHBoxLayout()
        btns_layout.addStretch(1)
        btns_layout.addWidget(cancel_btn, 0)
        btns_layout.addWidget(confirm_btn, 0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(top_widget, 0)
        layout.addStretch(1)
        layout.addWidget(question_label, 0)
        layout.addWidget(confirm_input, 0)
        layout.addLayout(btns_layout)

        cancel_btn.clicked.connect(self._on_cancel_click)
        confirm_btn.clicked.connect(self._on_confirm_click)
        confirm_input.textChanged.connect(self._on_confirm_text_change)
        confirm_input.returnPressed.connect(self._on_enter_clicked)

        self._cancel_btn = cancel_btn
        self._confirm_btn = confirm_btn
        self._confirm_input = confirm_input
        self._result = 0
        self._project_name = project_name

        self.setMinimumWidth(480)
        self.setMaximumWidth(650)
        self.setMaximumHeight(250)

    def exec_(self, *args, **kwargs):
        super(ConfirmProjectDeletion, self).exec_(*args, **kwargs)
        return self._result

    def showEvent(self, event):
        """Reset result on show."""
        super(ConfirmProjectDeletion, self).showEvent(event)
        self._result = 0
        minimum_size_hint = self.minimumSizeHint()
        self.resize(self.width(), minimum_size_hint.height() + 30)

    def result(self):
        """Get result of dialog 1 for confirm 0 for cancel."""
        return self._result

    def _on_cancel_click(self):
        self.close()

    def _on_confirm_click(self):
        self._result = 1
        self.close()

    def _on_enter_clicked(self):
        if self._confirm_btn.isEnabled():
            self._on_confirm_click()

    def _on_confirm_text_change(self):
        enabled = self._confirm_input.text() == self._project_name
        self._confirm_btn.setEnabled(enabled)


class SpinBoxScrollFixed(QtWidgets.QSpinBox):
    """QSpinBox which only allow edits change with scroll wheel when active"""
    def __init__(self, *args, **kwargs):
        super(SpinBoxScrollFixed, self).__init__(*args, **kwargs)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()
        else:
            super(SpinBoxScrollFixed, self).wheelEvent(event)


class DoubleSpinBoxScrollFixed(QtWidgets.QDoubleSpinBox):
    """QDoubleSpinBox which only allow edits with scroll wheel when active"""
    def __init__(self, *args, **kwargs):
        super(DoubleSpinBoxScrollFixed, self).__init__(*args, **kwargs)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def wheelEvent(self, event):
        if not self.hasFocus():
            event.ignore()
        else:
            super(DoubleSpinBoxScrollFixed, self).wheelEvent(event)
