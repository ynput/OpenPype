import os
import copy
import uuid
from Qt import QtWidgets, QtCore, QtGui
import qtawesome
from avalon.mongodb import (
    AvalonMongoConnection,
    AvalonMongoDB
)

from openpype.style import get_objected_colors
from openpype.tools.utils.widgets import ImageButton
from openpype.tools.utils.lib import paint_image_with_color

from openpype.widgets.nice_checkbox import NiceCheckbox
from openpype.tools.utils import (
    PlaceholderLineEdit,
    DynamicQThread
)
from openpype.settings.lib import find_closest_version_for_projects
from openpype.lib import get_openpype_version
from .images import (
    get_pixmap,
    get_image
)
from .constants import (
    DEFAULT_PROJECT_LABEL,
    PROJECT_NAME_ROLE,
    PROJECT_VERSION_ROLE,
    PROJECT_IS_ACTIVE_ROLE,
    PROJECT_IS_SELECTED_ROLE
)


class SettingsTabWidget(QtWidgets.QTabWidget):
    context_menu_requested = QtCore.Signal(int)

    def __init__(self, *args, **kwargs):
        super(SettingsTabWidget, self).__init__(*args, **kwargs)
        self._right_click_tab_idx = None

    def mousePressEvent(self, event):
        super(SettingsTabWidget, self).mousePressEvent(event)
        if event.button() == QtCore.Qt.RightButton:
            tab_bar = self.tabBar()
            pos = tab_bar.mapFromGlobal(event.globalPos())
            tab_idx = tab_bar.tabAt(pos)
            if tab_idx < 0:
                tab_idx = None
            self._right_click_tab_idx = tab_idx

    def mouseReleaseEvent(self, event):
        super(SettingsTabWidget, self).mouseReleaseEvent(event)
        if event.button() == QtCore.Qt.RightButton:
            tab_bar = self.tabBar()
            pos = tab_bar.mapFromGlobal(event.globalPos())
            tab_idx = tab_bar.tabAt(pos)
            if tab_idx == self._right_click_tab_idx:
                self.context_menu_requested.emit(tab_idx)
            self._right_click_tab = None


class CompleterFilter(QtCore.QSortFilterProxyModel):
    def __init__(self, *args, **kwargs):
        super(CompleterFilter, self).__init__(*args, **kwargs)

        self.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self._text_filter = ""

    def set_text_filter(self, text):
        if self._text_filter == text:
            return
        self._text_filter = text
        self.invalidateFilter()

    def filterAcceptsRow(self, row, parent_index):
        if not self._text_filter:
            return True
        model = self.sourceModel()
        index = model.index(row, self.filterKeyColumn(), parent_index)
        value = index.data(QtCore.Qt.DisplayRole)
        if self._text_filter in value:
            if self._text_filter == value:
                return False
            return True
        return False


class CompleterView(QtWidgets.QListView):
    row_activated = QtCore.Signal(str)

    def __init__(self, parent):
        super(CompleterView, self).__init__(parent)

        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.Tool
        )

        # Open the widget unactivated
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating)
        delegate = QtWidgets.QStyledItemDelegate()
        self.setItemDelegate(delegate)

        model = QtGui.QStandardItemModel()
        filter_model = CompleterFilter()
        filter_model.setSourceModel(model)
        self.setModel(filter_model)

        # self.installEventFilter(parent)

        self.clicked.connect(self._on_activated)

        self._last_loaded_values = None
        self._model = model
        self._filter_model = filter_model
        self._delegate = delegate

    def _on_activated(self, index):
        if index.isValid():
            value = index.data(QtCore.Qt.DisplayRole)
            self.row_activated.emit(value)

    def set_text_filter(self, text):
        self._filter_model.set_text_filter(text)
        self._update_geo()

    def sizeHint(self):
        result = super(CompleterView, self).sizeHint()
        if self._filter_model.rowCount() == 0:
            result.setHeight(0)

        return result

    def showEvent(self, event):
        super(CompleterView, self).showEvent(event)
        self._update_geo()

    def _update_geo(self):
        size_hint = self.sizeHint()
        self.resize(size_hint.width(), size_hint.height())

    def update_values(self, values):
        if not values:
            values = []

        if self._last_loaded_values == values:
            return
        self._last_loaded_values = copy.deepcopy(values)

        root_item = self._model.invisibleRootItem()
        existing_values = {}
        for row in reversed(range(root_item.rowCount())):
            child = root_item.child(row)
            value = child.data(QtCore.Qt.DisplayRole)
            if value not in values:
                root_item.removeRows(child.row())
            else:
                existing_values[value] = child

        for row, value in enumerate(values):
            if value in existing_values:
                item = existing_values[value]
                if item.row() == row:
                    continue
            else:
                item = QtGui.QStandardItem(value)
                item.setEditable(False)

            root_item.setChild(row, item)

        self._update_geo()

    def _get_selected_row(self):
        indexes = self.selectionModel().selectedIndexes()
        if not indexes:
            return -1
        return indexes[0].row()

    def _select_row(self, row):
        index = self._filter_model.index(row, 0)
        self.setCurrentIndex(index)

    def move_up(self):
        rows = self._filter_model.rowCount()
        if rows == 0:
            return

        selected_row = self._get_selected_row()
        if selected_row < 0:
            new_row = rows - 1
        else:
            new_row = selected_row - 1
            if new_row < 0:
                new_row = rows - 1

        if new_row != selected_row:
            self._select_row(new_row)

    def move_down(self):
        rows = self._filter_model.rowCount()
        if rows == 0:
            return

        selected_row = self._get_selected_row()
        if selected_row < 0:
            new_row = 0
        else:
            new_row = selected_row + 1
            if new_row >= rows:
                new_row = 0

        if new_row != selected_row:
            self._select_row(new_row)

    def enter_pressed(self):
        selected_row = self._get_selected_row()
        if selected_row < 0:
            return
        index = self._filter_model.index(selected_row, 0)
        self._on_activated(index)


class SettingsLineEdit(PlaceholderLineEdit):
    focused_in = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super(SettingsLineEdit, self).__init__(*args, **kwargs)

        # Timer which will get started on focus in and stopped on focus out
        # - callback checks if line edit or completer have focus
        #   and hide completer if not
        focus_timer = QtCore.QTimer()
        focus_timer.setInterval(50)

        focus_timer.timeout.connect(self._on_focus_timer)
        self.textChanged.connect(self._on_text_change)

        self._completer = None
        self._focus_timer = focus_timer

    def _on_text_change(self, text):
        if self._completer is not None:
            self._completer.set_text_filter(text)

    def _update_completer(self):
        if self._completer is None or not self._completer.isVisible():
            return
        point = self.frameGeometry().bottomLeft()
        new_point = self.mapToGlobal(point)
        self._completer.move(new_point)

    def _on_focus_timer(self):
        if not self.hasFocus() and not self._completer.hasFocus():
            self._completer.hide()
            self._focus_timer.stop()

    def focusInEvent(self, event):
        super(SettingsLineEdit, self).focusInEvent(event)
        self.focused_in.emit()

        if self._completer is not None:
            self._focus_timer.start()
            self._completer.show()
            self._update_completer()

    def paintEvent(self, event):
        super(SettingsLineEdit, self).paintEvent(event)
        self._update_completer()

    def update_completer_values(self, values):
        if not values and self._completer is None:
            return

        self._create_completer()

        self._completer.update_values(values)

    def _create_completer(self):
        if self._completer is None:
            self._completer = CompleterView(self)
            self._completer.row_activated.connect(self._completer_activated)

    def _completer_activated(self, text):
        self.setText(text)

    def keyPressEvent(self, event):
        if self._completer is None:
            super(SettingsLineEdit, self).keyPressEvent(event)
            return

        key = event.key()
        if key == QtCore.Qt.Key_Up:
            self._completer.move_up()
        elif key == QtCore.Qt.Key_Down:
            self._completer.move_down()
        elif key in (QtCore.Qt.Key_Enter, QtCore.Qt.Key_Return):
            self._completer.enter_pressed()
        else:
            super(SettingsLineEdit, self).keyPressEvent(event)


class SettingsPlainTextEdit(QtWidgets.QPlainTextEdit):
    focused_in = QtCore.Signal()

    def focusInEvent(self, event):
        super(SettingsPlainTextEdit, self).focusInEvent(event)
        self.focused_in.emit()


class SettingsToolBtn(ImageButton):
    _mask_pixmap = None
    _cached_icons = {}

    def __init__(self, btn_type, parent):
        super(SettingsToolBtn, self).__init__(parent)

        icon, hover_icon = self._get_icon_type(btn_type)

        self.setIcon(icon)

        self._icon = icon
        self._hover_icon = hover_icon

    @classmethod
    def _get_icon_type(cls, btn_type):
        if btn_type not in cls._cached_icons:
            settings_colors = get_objected_colors()["settings"]
            normal_color = settings_colors["image-btn"].get_qcolor()
            hover_color = settings_colors["image-btn-hover"].get_qcolor()
            disabled_color = settings_colors["image-btn-disabled"].get_qcolor()

            image = get_image("{}.png".format(btn_type))

            pixmap = paint_image_with_color(image, normal_color)
            hover_pixmap = paint_image_with_color(image, hover_color)
            disabled_pixmap = paint_image_with_color(image, disabled_color)

            icon = QtGui.QIcon(pixmap)
            hover_icon = QtGui.QIcon(hover_pixmap)
            icon.addPixmap(
                disabled_pixmap, QtGui.QIcon.Disabled, QtGui.QIcon.On
            )
            icon.addPixmap(
                disabled_pixmap, QtGui.QIcon.Disabled, QtGui.QIcon.Off
            )
            hover_icon.addPixmap(
                disabled_pixmap, QtGui.QIcon.Disabled, QtGui.QIcon.On
            )
            hover_icon.addPixmap(
                disabled_pixmap, QtGui.QIcon.Disabled, QtGui.QIcon.Off
            )
            cls._cached_icons[btn_type] = icon, hover_icon
        return cls._cached_icons[btn_type]

    def enterEvent(self, event):
        self.setIcon(self._hover_icon)
        super(SettingsToolBtn, self).enterEvent(event)

    def leaveEvent(self, event):
        self.setIcon(self._icon)
        super(SettingsToolBtn, self).leaveEvent(event)

    @classmethod
    def _get_mask_pixmap(cls):
        if cls._mask_pixmap is None:
            mask_pixmap = get_pixmap("mask.png")
            cls._mask_pixmap = mask_pixmap
        return cls._mask_pixmap

    def _change_size(self):
        super(SettingsToolBtn, self)._change_size()
        size = self.iconSize()
        scaled = self._get_mask_pixmap().scaled(
            size.width(),
            size.height(),
            QtCore.Qt.IgnoreAspectRatio,
            QtCore.Qt.SmoothTransformation
        )
        self.setMask(scaled.mask())


class ShadowWidget(QtWidgets.QWidget):
    def __init__(self, message, parent):
        super(ShadowWidget, self).__init__(parent)
        self.setObjectName("ShadowWidget")

        self.parent_widget = parent
        self.message = message

        def wrapper(func):
            def wrapped(*args, **kwarg):
                result = func(*args, **kwarg)
                self._update_geometry()
                return result
            return wrapped

        parent.resizeEvent = wrapper(parent.resizeEvent)
        parent.moveEvent = wrapper(parent.moveEvent)
        parent.showEvent = wrapper(parent.showEvent)

    def set_message(self, message):
        self.message = message
        if self.isVisible():
            self.repaint()

    def _update_geometry(self):
        self.setGeometry(self.parent_widget.rect())

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(
            event.rect(), QtGui.QBrush(QtGui.QColor(0, 0, 0, 127))
        )
        if self.message:
            painter.drawText(
                event.rect(),
                QtCore.Qt.AlignCenter | QtCore.Qt.AlignCenter,
                self.message
            )
        painter.end()


class IconButton(QtWidgets.QPushButton):
    def __init__(self, icon_name, color, hover_color, *args, **kwargs):
        super(IconButton, self).__init__(*args, **kwargs)

        self.icon = qtawesome.icon(icon_name, color=color)
        self.hover_icon = qtawesome.icon(icon_name, color=hover_color)

        self.setIcon(self.icon)

    def enterEvent(self, event):
        self.setIcon(self.hover_icon)
        super(IconButton, self).enterEvent(event)

    def leaveEvent(self, event):
        self.setIcon(self.icon)
        super(IconButton, self).leaveEvent(event)


class NumberSpinBox(QtWidgets.QDoubleSpinBox):
    focused_in = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        min_value = kwargs.pop("minimum", -99999)
        max_value = kwargs.pop("maximum", 99999)
        decimals = kwargs.pop("decimal", 0)
        steps = kwargs.pop("steps", None)

        super(NumberSpinBox, self).__init__(*args, **kwargs)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setDecimals(decimals)
        self.setMinimum(min_value)
        self.setMaximum(max_value)
        if steps is not None:
            self.setSingleStep(steps)

    def focusInEvent(self, event):
        super(NumberSpinBox, self).focusInEvent(event)
        self.focused_in.emit()

    def wheelEvent(self, event):
        if self.hasFocus():
            super(NumberSpinBox, self).wheelEvent(event)
        else:
            event.ignore()

    def value(self):
        output = super(NumberSpinBox, self).value()
        if self.decimals() == 0:
            output = int(output)
        return output


class SettingsComboBox(QtWidgets.QComboBox):
    value_changed = QtCore.Signal()
    focused_in = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super(SettingsComboBox, self).__init__(*args, **kwargs)

        delegate = QtWidgets.QStyledItemDelegate()
        self.setItemDelegate(delegate)

        self.currentIndexChanged.connect(self._on_change)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

        self._delegate = delegate

    def wheelEvent(self, event):
        if self.hasFocus():
            return super(SettingsComboBox, self).wheelEvent(event)

    def focusInEvent(self, event):
        self.focused_in.emit()
        return super(SettingsComboBox, self).focusInEvent(event)

    def _on_change(self, *args, **kwargs):
        self.value_changed.emit()

    def set_value(self, value):
        for idx in range(self.count()):
            _value = self.itemData(idx, role=QtCore.Qt.UserRole)
            if _value == value:
                self.setCurrentIndex(idx)
                break

    def value(self):
        return self.itemData(self.currentIndex(), role=QtCore.Qt.UserRole)


class ClickableWidget(QtWidgets.QWidget):
    clicked = QtCore.Signal()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()
        super(ClickableWidget, self).mouseReleaseEvent(event)


class ExpandingWidget(QtWidgets.QWidget):
    def __init__(self, label, parent):
        super(ExpandingWidget, self).__init__(parent)

        self.content_widget = None
        self.toolbox_hidden = False

        top_part = ClickableWidget(parent=self)

        side_line_widget = QtWidgets.QWidget(top_part)
        side_line_widget.setObjectName("SideLineWidget")

        button_size = QtCore.QSize(5, 5)
        button_toggle = QtWidgets.QToolButton(parent=side_line_widget)
        button_toggle.setObjectName("ExpandToggleBtn")
        button_toggle.setIconSize(button_size)
        button_toggle.setArrowType(QtCore.Qt.RightArrow)
        button_toggle.setCheckable(True)
        button_toggle.setChecked(False)

        label_widget = QtWidgets.QLabel(label, parent=side_line_widget)
        label_widget.setObjectName("ExpandLabel")

        before_label_widget = QtWidgets.QWidget(side_line_widget)
        before_label_layout = QtWidgets.QHBoxLayout(before_label_widget)
        before_label_layout.setContentsMargins(0, 0, 0, 0)

        after_label_widget = QtWidgets.QWidget(side_line_widget)
        after_label_layout = QtWidgets.QHBoxLayout(after_label_widget)
        after_label_layout.setContentsMargins(0, 0, 0, 0)

        side_line_layout = QtWidgets.QHBoxLayout(side_line_widget)
        side_line_layout.setContentsMargins(5, 10, 0, 10)
        side_line_layout.addWidget(button_toggle)
        side_line_layout.addWidget(before_label_widget)
        side_line_layout.addWidget(label_widget)
        side_line_layout.addWidget(after_label_widget)
        side_line_layout.addStretch(1)

        top_part_layout = QtWidgets.QHBoxLayout(top_part)
        top_part_layout.setContentsMargins(0, 0, 0, 0)
        top_part_layout.addWidget(side_line_widget)

        before_label_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        after_label_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        label_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.top_part_ending = None
        self.after_label_layout = after_label_layout
        self.before_label_layout = before_label_layout

        self.side_line_widget = side_line_widget
        self.side_line_layout = side_line_layout
        self.button_toggle = button_toggle
        self.label_widget = label_widget

        top_part.clicked.connect(self._top_part_clicked)
        self.button_toggle.clicked.connect(self._btn_clicked)

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        self.main_layout.addWidget(top_part)

        self.top_part = top_part

    def hide_toolbox(self, hide_content=False):
        self.button_toggle.setArrowType(QtCore.Qt.NoArrow)
        self.toolbox_hidden = True
        if self.content_widget:
            self.content_widget.setVisible(not hide_content)
        self.parent().updateGeometry()

    def show_toolbox(self):
        self.toolbox_hidden = False
        self.toggle_content(self.button_toggle.isChecked())

        self.parent().updateGeometry()

    def set_content_widget(self, content_widget):
        content_widget.setVisible(False)
        self.main_layout.addWidget(content_widget)
        self.content_widget = content_widget

    def is_expanded(self):
        return self.button_toggle.isChecked()

    def _btn_clicked(self):
        self.toggle_content(self.button_toggle.isChecked())

    def _top_part_clicked(self):
        self.toggle_content()

    def toggle_content(self, *args):
        if self.toolbox_hidden:
            return

        if len(args) > 0:
            checked = args[0]
        else:
            checked = not self.button_toggle.isChecked()
        arrow_type = QtCore.Qt.RightArrow
        if checked:
            arrow_type = QtCore.Qt.DownArrow
        self.button_toggle.setChecked(checked)
        self.button_toggle.setArrowType(arrow_type)
        if self.content_widget:
            self.content_widget.setVisible(checked)
        self.parent().updateGeometry()

    def add_widget_after_label(self, widget):
        self.after_label_layout.addWidget(widget)

    def add_widget_before_label(self, widget):
        self.before_label_layout.addWidget(widget)

    def resizeEvent(self, event):
        super(ExpandingWidget, self).resizeEvent(event)
        if self.content_widget:
            self.content_widget.updateGeometry()


class UnsavedChangesDialog(QtWidgets.QDialog):
    message = "You have unsaved changes. What do you want to do with them?"

    def __init__(self, parent=None):
        super(UnsavedChangesDialog, self).__init__(parent)
        message_label = QtWidgets.QLabel(self.message)

        btns_widget = QtWidgets.QWidget(self)
        btns_layout = QtWidgets.QHBoxLayout(btns_widget)

        btn_ok = QtWidgets.QPushButton("Save")
        btn_ok.clicked.connect(self.on_ok_pressed)
        btn_discard = QtWidgets.QPushButton("Discard")
        btn_discard.clicked.connect(self.on_discard_pressed)
        btn_cancel = QtWidgets.QPushButton("Cancel")
        btn_cancel.clicked.connect(self.on_cancel_pressed)

        btns_layout.addWidget(btn_ok)
        btns_layout.addWidget(btn_discard)
        btns_layout.addWidget(btn_cancel)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(message_label)
        layout.addWidget(btns_widget)

    def on_cancel_pressed(self):
        self.done(0)

    def on_ok_pressed(self):
        self.done(1)

    def on_discard_pressed(self):
        self.done(2)


class RestartDialog(QtWidgets.QDialog):
    message = (
        "Your changes require restart of process to take effect."
        " Do you want to restart now?"
    )

    def __init__(self, parent=None):
        super(RestartDialog, self).__init__(parent)
        message_label = QtWidgets.QLabel(self.message)

        btns_widget = QtWidgets.QWidget(self)
        btns_layout = QtWidgets.QHBoxLayout(btns_widget)

        btn_restart = QtWidgets.QPushButton("Restart")
        btn_restart.clicked.connect(self.on_restart_pressed)
        btn_cancel = QtWidgets.QPushButton("Cancel")
        btn_cancel.clicked.connect(self.on_cancel_pressed)

        btns_layout.addStretch(1)
        btns_layout.addWidget(btn_restart)
        btns_layout.addWidget(btn_cancel)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(message_label)
        layout.addWidget(btns_widget)

        self.btn_cancel = btn_cancel
        self.btn_restart = btn_restart

    def showEvent(self, event):
        super(RestartDialog, self).showEvent(event)
        btns_width = max(self.btn_cancel.width(), self.btn_restart.width())
        self.btn_cancel.setFixedWidth(btns_width)
        self.btn_restart.setFixedWidth(btns_width)

    def on_cancel_pressed(self):
        self.done(0)

    def on_restart_pressed(self):
        self.done(1)


class SpacerWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(SpacerWidget, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)


class GridLabelWidget(QtWidgets.QWidget):
    def __init__(self, label, parent=None):
        super(GridLabelWidget, self).__init__(parent)

        self.input_field = None

        self.properties = {}

        label_widget = QtWidgets.QLabel(label, self)
        label_widget.setObjectName("SettingsLabel")

        label_proxy_layout = QtWidgets.QHBoxLayout()
        label_proxy_layout.setContentsMargins(0, 0, 0, 0)
        label_proxy_layout.setSpacing(0)

        label_proxy_layout.addWidget(label_widget, 0, QtCore.Qt.AlignRight)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 0)
        layout.setSpacing(0)

        layout.addLayout(label_proxy_layout, 0)
        layout.addStretch(1)

        label_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self.label_widget = label_widget

    def setProperty(self, name, value):
        cur_value = self.properties.get(name)
        if cur_value == value:
            return

        self.label_widget.setProperty(name, value)
        self.label_widget.style().polish(self.label_widget)

    def mouseReleaseEvent(self, event):
        if self.input_field:
            if event and event.button() == QtCore.Qt.LeftButton:
                self.input_field.focused_in()
            return self.input_field.show_actions_menu(event)
        return super(GridLabelWidget, self).mouseReleaseEvent(event)


class SettingsNiceCheckbox(NiceCheckbox):
    focused_in = QtCore.Signal()

    def mousePressEvent(self, event):
        self.focused_in.emit()
        super(SettingsNiceCheckbox, self).mousePressEvent(event)


class ProjectModel(QtGui.QStandardItemModel):
    _update_versions = QtCore.Signal()

    def __init__(self, only_active, *args, **kwargs):
        super(ProjectModel, self).__init__(*args, **kwargs)

        self.setColumnCount(2)

        self.dbcon = None

        self._only_active = only_active
        self._default_item = None
        self._items_by_name = {}
        self._versions_by_project = {}

        colors = get_objected_colors()
        font_color = colors["font"].get_qcolor()
        font_color.setAlpha(67)
        self._version_font_color = font_color
        self._current_version = get_openpype_version()

        self._version_refresh_threads = []
        self._version_refresh_id = None

        self._update_versions.connect(self._on_update_versions_signal)

    def _on_update_versions_signal(self):
        for project_name, version in self._versions_by_project.items():
            if project_name is None:
                item = self._default_item
            else:
                item = self._items_by_name.get(project_name)

            if item and version != self._current_version:
                item.setData(version, PROJECT_VERSION_ROLE)

    def _fetch_settings_versions(self):
        """Used versions per project are loaded in thread to not stuck UI."""
        version_refresh_id = self._version_refresh_id
        all_project_names = list(self._items_by_name.keys())
        all_project_names.append(None)
        closest_by_project_name = find_closest_version_for_projects(
            all_project_names
        )
        if self._version_refresh_id == version_refresh_id:
            self._versions_by_project = closest_by_project_name
            self._update_versions.emit()

    def flags(self, index):
        if index.column() == 1:
            index = self.index(index.row(), 0, index.parent())
        return super(ProjectModel, self).flags(index)

    def set_dbcon(self, dbcon):
        self.dbcon = dbcon

    def refresh(self):
        # Change id of versions refresh
        self._version_refresh_id = uuid.uuid4()

        new_items = []
        if self._default_item is None:
            item = QtGui.QStandardItem(DEFAULT_PROJECT_LABEL)
            item.setData(None, PROJECT_NAME_ROLE)
            item.setData(True, PROJECT_IS_ACTIVE_ROLE)
            item.setData(False, PROJECT_IS_SELECTED_ROLE)
            new_items.append(item)
            self._default_item = item

        self._default_item.setData("", PROJECT_VERSION_ROLE)
        project_names = set()
        if self.dbcon is not None:
            for project_doc in self.dbcon.projects(
                projection={"name": 1, "data.active": 1},
                only_active=self._only_active
            ):
                project_name = project_doc["name"]
                project_names.add(project_name)
                if project_name in self._items_by_name:
                    item = self._items_by_name[project_name]
                else:
                    item = QtGui.QStandardItem(project_name)

                    self._items_by_name[project_name] = item
                    new_items.append(item)

                is_active = project_doc.get("data", {}).get("active", True)
                item.setData(project_name, PROJECT_NAME_ROLE)
                item.setData(is_active, PROJECT_IS_ACTIVE_ROLE)
                item.setData("", PROJECT_VERSION_ROLE)
                item.setData(False, PROJECT_IS_SELECTED_ROLE)

                if not is_active:
                    font = item.font()
                    font.setItalic(True)
                    item.setFont(font)

        root_item = self.invisibleRootItem()
        for project_name in tuple(self._items_by_name.keys()):
            if project_name not in project_names:
                item = self._items_by_name.pop(project_name)
                root_item.removeRow(item.row())

        if new_items:
            root_item.appendRows(new_items)

        # Fetch versions per project in thread
        thread = DynamicQThread(self._fetch_settings_versions)
        self._version_refresh_threads.append(thread)
        thread.start()

        # Cleanup done threads
        for thread in tuple(self._version_refresh_threads):
            if thread.isFinished():
                self._version_refresh_threads.remove(thread)

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if index.column() == 1:
            if role == QtCore.Qt.TextAlignmentRole:
                return QtCore.Qt.AlignRight
            if role == QtCore.Qt.ForegroundRole:
                return self._version_font_color
            index = self.index(index.row(), 0, index.parent())
            if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
                role = PROJECT_VERSION_ROLE

        return super(ProjectModel, self).data(index, role)

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if index.column() == 1:
            index = self.index(index.row(), 0, index.parent())
            if role in (QtCore.Qt.DisplayRole, QtCore.Qt.EditRole):
                role = PROJECT_VERSION_ROLE
        return super(ProjectModel, self).setData(index, value, role)

    def headerData(self, section, orientation, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            if section == 0:
                return "Project name"

            elif section == 1:
                return "Used version"
            return ""
        return super(ProjectModel, self).headerData(
            section, orientation, role
        )


class VersionAction(QtWidgets.QAction):
    version_triggered = QtCore.Signal(str)

    def __init__(self, version, *args, **kwargs):
        super(VersionAction, self).__init__(version, *args, **kwargs)
        self._version = version
        self.triggered.connect(self._on_trigger)

    def _on_trigger(self):
        self.version_triggered.emit(self._version)


class ProjectView(QtWidgets.QTreeView):
    left_mouse_released_at = QtCore.Signal(QtCore.QModelIndex)
    right_mouse_released_at = QtCore.Signal(QtCore.QModelIndex)

    def __init__(self, *args, **kwargs):
        super(ProjectView, self).__init__(*args, **kwargs)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.setIndentation(0)

        # Do not allow editing
        self.setEditTriggers(
            QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
        )
        # Do not automatically handle selection
        self.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            index = self.indexAt(event.pos())
            self.left_mouse_released_at.emit(index)

        elif event.button() == QtCore.Qt.RightButton:
            index = self.indexAt(event.pos())
            self.right_mouse_released_at.emit(index)

        super(ProjectView, self).mouseReleaseEvent(event)


class ProjectSortFilterProxy(QtCore.QSortFilterProxyModel):
    def __init__(self, *args, **kwargs):
        super(ProjectSortFilterProxy, self).__init__(*args, **kwargs)
        self._enable_filter = True

    def lessThan(self, left_index, right_index):
        if left_index.data(PROJECT_NAME_ROLE) is None:
            return True

        if right_index.data(PROJECT_NAME_ROLE) is None:
            return False

        left_is_active = left_index.data(PROJECT_IS_ACTIVE_ROLE)
        right_is_active = right_index.data(PROJECT_IS_ACTIVE_ROLE)
        if right_is_active == left_is_active:
            return super(ProjectSortFilterProxy, self).lessThan(
                left_index, right_index
            )

        if left_is_active:
            return True
        return False

    def filterAcceptsRow(self, source_row, source_parent):
        if not self._enable_filter:
            return True

        index = self.sourceModel().index(source_row, 0, source_parent)
        is_active = bool(index.data(self.filterRole()))
        is_selected = bool(index.data(PROJECT_IS_SELECTED_ROLE))

        return is_active or is_selected

    def is_filter_enabled(self):
        return self._enable_filter

    def set_filter_enabled(self, value):
        self._enable_filter = value
        self.invalidateFilter()


class ProjectListWidget(QtWidgets.QWidget):
    project_changed = QtCore.Signal()
    version_change_requested = QtCore.Signal(str)

    def __init__(self, parent, only_active=False):
        self._parent = parent

        self._entity = None
        self.current_project = None

        super(ProjectListWidget, self).__init__(parent)
        self.setObjectName("ProjectListWidget")

        content_frame = QtWidgets.QFrame(self)
        content_frame.setObjectName("ProjectListContentWidget")

        project_list = ProjectView(content_frame)
        project_model = ProjectModel(only_active)
        project_proxy = ProjectSortFilterProxy()

        project_proxy.setFilterRole(PROJECT_IS_ACTIVE_ROLE)
        project_proxy.setSourceModel(project_model)
        project_list.setModel(project_proxy)

        content_layout = QtWidgets.QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(project_list, 1)

        inactive_chk = None
        if not only_active:
            checkbox_wrapper = QtWidgets.QWidget(content_frame)
            checkbox_wrapper.setAttribute(QtCore.Qt.WA_TranslucentBackground)

            inactive_chk = QtWidgets.QCheckBox(
                "Show Inactive Projects", checkbox_wrapper
            )
            inactive_chk.setChecked(not project_proxy.is_filter_enabled())

            wrapper_layout = QtWidgets.QHBoxLayout(checkbox_wrapper)
            wrapper_layout.addWidget(inactive_chk, 1)

            content_layout.addWidget(checkbox_wrapper, 0)

            inactive_chk.stateChanged.connect(self.on_inactive_vis_changed)

        layout = QtWidgets.QVBoxLayout(self)
        # Margins '3' are matching to configurables widget scroll area on right
        layout.setContentsMargins(5, 3, 3, 3)
        layout.addWidget(content_frame, 1)

        project_list.left_mouse_released_at.connect(self.on_item_clicked)
        project_list.right_mouse_released_at.connect(
            self._on_item_right_clicked
        )

        self.project_list = project_list
        self.project_proxy = project_proxy
        self.project_model = project_model
        self.inactive_chk = inactive_chk

        self.dbcon = None

    def set_entity(self, entity):
        self._entity = entity

    def _on_item_right_clicked(self, index):
        if not index.isValid():
            return
        project_name = index.data(PROJECT_NAME_ROLE)
        if project_name is None:
            project_name = DEFAULT_PROJECT_LABEL

        if self.current_project != project_name:
            self.on_item_clicked(index)

        if self.current_project != project_name:
            return

        if not self._entity:
            return

        versions = self._entity.get_available_source_versions(sorted=True)
        if not versions:
            return

        menu = QtWidgets.QMenu(self)
        submenu = QtWidgets.QMenu("Use settings from version", menu)
        for version in reversed(versions):
            action = VersionAction(version, submenu)
            action.version_triggered.connect(
                self.version_change_requested
            )
            submenu.addAction(action)
        menu.addMenu(submenu)
        menu.exec_(QtGui.QCursor.pos())

    def on_item_clicked(self, new_index):
        if not new_index.isValid():
            return
        new_project_name = new_index.data(PROJECT_NAME_ROLE)
        if new_project_name is None:
            new_project_name = DEFAULT_PROJECT_LABEL

        if self.current_project == new_project_name:
            return

        save_changes = False
        change_project = False
        if self.validate_context_change():
            change_project = True

        else:
            dialog = UnsavedChangesDialog(self)
            result = dialog.exec_()
            if result == 1:
                save_changes = True
                change_project = True

            elif result == 2:
                change_project = True

        if save_changes:
            self._parent._save()

        if change_project:
            self.select_project(new_project_name)
            self.current_project = new_project_name
            self.project_changed.emit()
        else:
            self.select_project(self.current_project)

    def on_inactive_vis_changed(self):
        if self.inactive_chk is None:
            # should not happen.
            return

        enable_filter = not self.inactive_chk.isChecked()
        self.project_proxy.set_filter_enabled(enable_filter)

    def validate_context_change(self):
        return not self._parent.entity.has_unsaved_changes

    def project_name(self):
        if self.current_project == DEFAULT_PROJECT_LABEL:
            return None
        return self.current_project

    def select_default_project(self):
        self.select_project(DEFAULT_PROJECT_LABEL)

    def select_project(self, project_name):
        model = self.project_model
        proxy = self.project_proxy

        found_items = model.findItems(project_name)
        if not found_items:
            found_items = model.findItems(DEFAULT_PROJECT_LABEL)

        index = model.indexFromItem(found_items[0])
        model.setData(index, True, PROJECT_IS_SELECTED_ROLE)

        src_indexes = []
        col_count = model.columnCount()
        if col_count > 1:
            for col in range(col_count):
                src_indexes.append(
                    model.index(index.row(), col, index.parent())
                )
        dst_indexes = []
        for index in src_indexes:
            dst_indexes.append(proxy.mapFromSource(index))

        selection_model = self.project_list.selectionModel()
        selection_model.clear()

        first = True
        for index in dst_indexes:
            if first:
                selection_model.setCurrentIndex(
                    index,
                    QtCore.QItemSelectionModel.SelectionFlag.SelectCurrent
                )
                first = False
                continue
            selection_model.select(index, QtCore.QItemSelectionModel.Select)

    def get_project_names(self):
        output = []
        for row in range(self.project_proxy.rowCount()):
            index = self.project_proxy.index(row, 0)
            output.append(index.data(PROJECT_NAME_ROLE))
        return output

    def refresh(self):
        selected_project = None
        for index in self.project_list.selectedIndexes():
            selected_project = index.data(PROJECT_NAME_ROLE)
            break

        mongo_url = os.environ["OPENPYPE_MONGO"]

        # Force uninstall of whole avalon connection if url does not match
        # to current environment and set it as environment
        if mongo_url != os.environ["AVALON_MONGO"]:
            AvalonMongoConnection.uninstall(self.dbcon, force=True)
            os.environ["AVALON_MONGO"] = mongo_url
            self.dbcon = None

        if not self.dbcon:
            try:
                self.dbcon = AvalonMongoDB()
                self.dbcon.install()
            except Exception:
                self.dbcon = None
                self.current_project = None

        self.project_model.set_dbcon(self.dbcon)
        self.project_model.refresh()

        self.project_proxy.sort(0)

        self.select_project(selected_project)

        self.current_project = self.project_list.currentIndex().data(
            PROJECT_NAME_ROLE
        )
        self.project_list.resizeColumnToContents(0)
