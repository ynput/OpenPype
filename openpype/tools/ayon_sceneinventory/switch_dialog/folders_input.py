from qtpy import QtWidgets, QtCore
import qtawesome

from openpype.tools.utils import (
    PlaceholderLineEdit,
    BaseClickableFrame,
    set_style_property,
)
from openpype.tools.ayon_utils.widgets import FoldersWidget

NOT_SET = object()


class ClickableLineEdit(QtWidgets.QLineEdit):
    """QLineEdit capturing left mouse click.

    Triggers `clicked` signal on mouse click.
    """
    clicked = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super(ClickableLineEdit, self).__init__(*args, **kwargs)
        self.setReadOnly(True)
        self._mouse_pressed = False

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._mouse_pressed = True
        event.accept()

    def mouseMoveEvent(self, event):
        event.accept()

    def mouseReleaseEvent(self, event):
        if self._mouse_pressed:
            self._mouse_pressed = False
            if self.rect().contains(event.pos()):
                self.clicked.emit()
        event.accept()

    def mouseDoubleClickEvent(self, event):
        event.accept()


class ControllerWrap:
    def __init__(self, controller):
        self._controller = controller
        self._selected_folder_id = None

    def emit_event(self, *args, **kwargs):
        self._controller.emit_event(*args, **kwargs)

    def register_event_callback(self, *args, **kwargs):
        self._controller.register_event_callback(*args, **kwargs)

    def get_current_project_name(self):
        return self._controller.get_current_project_name()

    def get_folder_items(self, *args, **kwargs):
        return self._controller.get_folder_items(*args, **kwargs)

    def set_selected_folder(self, folder_id):
        self._selected_folder_id = folder_id

    def get_selected_folder_id(self):
        return self._selected_folder_id


class FoldersDialog(QtWidgets.QDialog):
    """Dialog to select asset for a context of instance."""

    def __init__(self, controller, parent):
        super(FoldersDialog, self).__init__(parent)
        self.setWindowTitle("Select folder")

        filter_input = PlaceholderLineEdit(self)
        filter_input.setPlaceholderText("Filter folders..")

        controller_wrap = ControllerWrap(controller)
        folders_widget = FoldersWidget(controller_wrap, self)
        folders_widget.set_deselectable(True)

        ok_btn = QtWidgets.QPushButton("OK", self)
        cancel_btn = QtWidgets.QPushButton("Cancel", self)

        btns_layout = QtWidgets.QHBoxLayout()
        btns_layout.addStretch(1)
        btns_layout.addWidget(ok_btn)
        btns_layout.addWidget(cancel_btn)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(filter_input, 0)
        layout.addWidget(folders_widget, 1)
        layout.addLayout(btns_layout, 0)

        folders_widget.double_clicked.connect(self._on_ok_clicked)
        folders_widget.refreshed.connect(self._on_folders_refresh)
        filter_input.textChanged.connect(self._on_filter_change)
        ok_btn.clicked.connect(self._on_ok_clicked)
        cancel_btn.clicked.connect(self._on_cancel_clicked)

        self._filter_input = filter_input
        self._ok_btn = ok_btn
        self._cancel_btn = cancel_btn

        self._folders_widget = folders_widget
        self._controller_wrap = controller_wrap

        # Set selected folder only when user confirms the dialog
        self._selected_folder_id = None
        self._selected_folder_label = None

        self._folder_id_to_select = NOT_SET

        self._first_show = True
        self._default_height = 500

    def showEvent(self, event):
        """Refresh asset model on show."""
        super(FoldersDialog, self).showEvent(event)
        if self._first_show:
            self._first_show = False
            self._on_first_show()

    def refresh(self):
        project_name = self._controller_wrap.get_current_project_name()
        self._folders_widget.set_project_name(project_name)

    def _on_first_show(self):
        center = self.rect().center()
        size = self.size()
        size.setHeight(self._default_height)

        self.resize(size)
        new_pos = self.mapToGlobal(center)
        new_pos.setX(new_pos.x() - int(self.width() / 2))
        new_pos.setY(new_pos.y() - int(self.height() / 2))
        self.move(new_pos)

    def _on_folders_refresh(self):
        if self._folder_id_to_select is NOT_SET:
            return
        self._folders_widget.set_selected_folder(self._folder_id_to_select)
        self._folder_id_to_select = NOT_SET

    def _on_filter_change(self, text):
        """Trigger change of filter of folders."""

        self._folders_widget.set_name_filter(text)

    def _on_cancel_clicked(self):
        self.done(0)

    def _on_ok_clicked(self):
        self._selected_folder_id = (
            self._folders_widget.get_selected_folder_id()
        )
        self._selected_folder_label = (
            self._folders_widget.get_selected_folder_label()
        )
        self.done(1)

    def set_selected_folder(self, folder_id):
        """Change preselected folder before showing the dialog.

        This also resets model and clean filter.
        """

        if (
            self._folders_widget.is_refreshing
            or self._folders_widget.get_project_name() is None
        ):
            self._folder_id_to_select = folder_id
        else:
            self._folders_widget.set_selected_folder(folder_id)

    def get_selected_folder_id(self):
        """Get selected folder id.

        Returns:
            Union[str, None]: Selected folder id or None if nothing
                is selected.
        """
        return self._selected_folder_id

    def get_selected_folder_label(self):
        return self._selected_folder_label


class FoldersField(BaseClickableFrame):
    """Field where asset name of selected instance/s is showed.

    Click on the field will trigger `FoldersDialog`.
    """
    value_changed = QtCore.Signal()

    def __init__(self, controller, parent):
        super(FoldersField, self).__init__(parent)
        self.setObjectName("AssetNameInputWidget")

        # Don't use 'self' for parent!
        # - this widget has specific styles
        dialog = FoldersDialog(controller, parent)

        name_input = ClickableLineEdit(self)
        name_input.setObjectName("AssetNameInput")

        icon = qtawesome.icon("fa.window-maximize", color="white")
        icon_btn = QtWidgets.QPushButton(self)
        icon_btn.setIcon(icon)
        icon_btn.setObjectName("AssetNameInputButton")

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(name_input, 1)
        layout.addWidget(icon_btn, 0)

        # Make sure all widgets are vertically extended to highest widget
        for widget in (
            name_input,
            icon_btn
        ):
            w_size_policy = widget.sizePolicy()
            w_size_policy.setVerticalPolicy(
                QtWidgets.QSizePolicy.MinimumExpanding)
            widget.setSizePolicy(w_size_policy)

        size_policy = self.sizePolicy()
        size_policy.setVerticalPolicy(QtWidgets.QSizePolicy.Maximum)
        self.setSizePolicy(size_policy)

        name_input.clicked.connect(self._mouse_release_callback)
        icon_btn.clicked.connect(self._mouse_release_callback)
        dialog.finished.connect(self._on_dialog_finish)

        self._controller = controller
        self._dialog = dialog
        self._name_input = name_input
        self._icon_btn = icon_btn

        self._selected_folder_id = None
        self._selected_folder_label = None
        self._selected_items = []
        self._is_valid = True

    def refresh(self):
        self._dialog.refresh()

    def is_valid(self):
        """Is asset valid."""
        return self._is_valid

    def get_selected_folder_id(self):
        """Selected asset names."""
        return self._selected_folder_id

    def get_selected_folder_label(self):
        return self._selected_folder_label

    def set_text(self, text):
        """Set text in text field.

        Does not change selected items (assets).
        """
        self._name_input.setText(text)

    def set_valid(self, is_valid):
        state = ""
        if not is_valid:
            state = "invalid"
        self._set_state_property(state)

    def set_selected_item(self, folder_id=None, folder_label=None):
        """Set folder for selection.

        Args:
            folder_id (Optional[str]): Folder id to select.
            folder_label (Optional[str]): Folder label.
        """

        self._selected_folder_id = folder_id
        if not folder_id:
            folder_label = None
        elif folder_id and not folder_label:
            folder_label = self._controller.get_folder_label(folder_id)
        self._selected_folder_label = folder_label
        self.set_text(folder_label if folder_label else "<folder>")

    def _on_dialog_finish(self, result):
        if not result:
            return

        folder_id = self._dialog.get_selected_folder_id()
        folder_label = self._dialog.get_selected_folder_label()
        self.set_selected_item(folder_id, folder_label)

        self.value_changed.emit()

    def _mouse_release_callback(self):
        self._dialog.set_selected_folder(self._selected_folder_id)
        self._dialog.open()

    def _set_state_property(self, state):
        set_style_property(self, "state", state)
        set_style_property(self._name_input, "state", state)
        set_style_property(self._icon_btn, "state", state)
