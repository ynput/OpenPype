# -*- coding: utf-8 -*-
import collections
import logging

try:
    import commonmark
except Exception:
    commonmark = None

from qtpy import QtWidgets, QtCore, QtGui

from openpype.style import get_objected_colors
from openpype.tools.utils import (
    BaseClickableFrame,
    ClickableFrame,
    ExpandingTextEdit,
    FlowLayout,
    ClassicExpandBtn,
    paint_image_with_color,
    SeparatorWidget,
)
from .widgets import IconValuePixmapLabel
from .icons import (
    get_pixmap,
    get_image,
)
from ..constants import (
    INSTANCE_ID_ROLE,
    CONTEXT_ID,
    CONTEXT_LABEL,
)

LOG_DEBUG_VISIBLE = 1 << 0
LOG_INFO_VISIBLE = 1 << 1
LOG_WARNING_VISIBLE = 1 << 2
LOG_ERROR_VISIBLE = 1 << 3
LOG_CRITICAL_VISIBLE = 1 << 4
ERROR_VISIBLE = 1 << 5
INFO_VISIBLE = 1 << 6


class VerticalScrollArea(QtWidgets.QScrollArea):
    """Scroll area for validation error titles.

    The biggest difference is that the scroll area has scroll bar on left side
    and resize of content will also resize scrollarea itself.

    Resize if deferred by 100ms because at the moment of resize are not yet
    propagated sizes and visibility of scroll bars.
    """

    def __init__(self, *args, **kwargs):
        super(VerticalScrollArea, self).__init__(*args, **kwargs)

        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self.setLayoutDirection(QtCore.Qt.RightToLeft)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        # Background of scrollbar will be transparent
        scrollbar_bg = self.verticalScrollBar().parent()
        if scrollbar_bg:
            scrollbar_bg.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setViewportMargins(0, 0, 0, 0)

        self.verticalScrollBar().installEventFilter(self)

        # Timer with 100ms offset after changing size
        size_changed_timer = QtCore.QTimer()
        size_changed_timer.setInterval(100)
        size_changed_timer.setSingleShot(True)

        size_changed_timer.timeout.connect(self._on_timer_timeout)
        self._size_changed_timer = size_changed_timer

    def setVerticalScrollBar(self, widget):
        old_widget = self.verticalScrollBar()
        if old_widget:
            old_widget.removeEventFilter(self)

        super(VerticalScrollArea, self).setVerticalScrollBar(widget)
        if widget:
            widget.installEventFilter(self)

    def setWidget(self, widget):
        old_widget = self.widget()
        if old_widget:
            old_widget.removeEventFilter(self)

        super(VerticalScrollArea, self).setWidget(widget)
        if widget:
            widget.installEventFilter(self)

    def _on_timer_timeout(self):
        width = self.widget().width()
        if self.verticalScrollBar().isVisible():
            width += self.verticalScrollBar().width()
        self.setMinimumWidth(width)

    def eventFilter(self, obj, event):
        if (
            event.type() == QtCore.QEvent.Resize
            and (obj is self.widget() or obj is self.verticalScrollBar())
        ):
            self._size_changed_timer.start()
        return super(VerticalScrollArea, self).eventFilter(obj, event)


# --- Publish actions widget ---
class ActionButton(BaseClickableFrame):
    """Plugin's action callback button.

    Action may have label or icon or both.

    Args:
        plugin_action_item (PublishPluginActionItem): Action item that can be
            triggered by its id.
    """

    action_clicked = QtCore.Signal(str, str)

    def __init__(self, plugin_action_item, parent):
        super(ActionButton, self).__init__(parent)

        self.setObjectName("ValidationActionButton")

        self.plugin_action_item = plugin_action_item

        action_label = plugin_action_item.label
        action_icon = plugin_action_item.icon
        label_widget = QtWidgets.QLabel(action_label, self)
        icon_label = None
        if action_icon:
            icon_label = IconValuePixmapLabel(action_icon, self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.addWidget(label_widget, 1)
        if icon_label:
            layout.addWidget(icon_label, 0)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            self.sizePolicy().verticalPolicy()
        )

    def _mouse_release_callback(self):
        self.action_clicked.emit(
            self.plugin_action_item.plugin_id,
            self.plugin_action_item.action_id
        )


class ValidateActionsWidget(QtWidgets.QFrame):
    """Wrapper widget for plugin actions.

    Change actions based on selected validation error.
    """

    def __init__(self, controller, parent):
        super(ValidateActionsWidget, self).__init__(parent)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        content_widget = QtWidgets.QWidget(self)
        content_layout = FlowLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(content_widget)

        self._controller = controller
        self._content_widget = content_widget
        self._content_layout = content_layout

        self._actions_mapping = {}

        self._visible_mode = True

    def _update_visibility(self):
        self.setVisible(
            self._visible_mode
            and self._content_layout.count() > 0
        )

    def set_visible_mode(self, visible):
        if self._visible_mode is visible:
            return
        self._visible_mode = visible
        self._update_visibility()

    def _clear(self):
        """Remove actions from widget."""
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setVisible(False)
                widget.deleteLater()
        self._actions_mapping = {}

    def set_error_info(self, error_info):
        """Set selected plugin and show it's actions.

        Clears current actions from widget and recreate them from the plugin.

        Args:
            Dict[str, Any]: Object holding error items, title and possible
                actions to run.
        """

        self._clear()

        if not error_info:
            self.setVisible(False)
            return

        plugin_action_items = error_info["plugin_action_items"]
        for plugin_action_item in plugin_action_items:
            if not plugin_action_item.active:
                continue

            if plugin_action_item.on_filter not in ("failed", "all"):
                continue

            action_id = plugin_action_item.action_id
            self._actions_mapping[action_id] = plugin_action_item

            action_btn = ActionButton(plugin_action_item, self._content_widget)
            action_btn.action_clicked.connect(self._on_action_click)
            self._content_layout.addWidget(action_btn)

        self._update_visibility()

    def _on_action_click(self, plugin_id, action_id):
        self._controller.run_action(plugin_id, action_id)


# --- Validation error titles ---
class ValidationErrorInstanceList(QtWidgets.QListView):
    """List of publish instances that caused a validation error.

    Instances are collected per plugin's validation error title.
    """
    def __init__(self, *args, **kwargs):
        super(ValidationErrorInstanceList, self).__init__(*args, **kwargs)

        self.setObjectName("ValidationErrorInstanceList")

        self.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

    def minimumSizeHint(self):
        return self.sizeHint()

    def sizeHint(self):
        result = super(ValidationErrorInstanceList, self).sizeHint()
        row_count = self.model().rowCount()
        height = 0
        if row_count > 0:
            height = self.sizeHintForRow(0) * row_count
        result.setHeight(height)
        return result


class ValidationErrorTitleWidget(QtWidgets.QWidget):
    """Title of validation error.

    Widget is used as radio button so requires clickable functionality and
    changing style on selection/deselection.

    Has toggle button to show/hide instances on which validation error happened
    if there is a list (Valdation error may happen on context).
    """

    selected = QtCore.Signal(str)
    instance_changed = QtCore.Signal(str)

    def __init__(self, title_id, error_info, parent):
        super(ValidationErrorTitleWidget, self).__init__(parent)

        self._title_id = title_id
        self._error_info = error_info
        self._selected = False

        title_frame = ClickableFrame(self)
        title_frame.setObjectName("ValidationErrorTitleFrame")

        toggle_instance_btn = QtWidgets.QToolButton(title_frame)
        toggle_instance_btn.setObjectName("ArrowBtn")
        toggle_instance_btn.setArrowType(QtCore.Qt.RightArrow)
        toggle_instance_btn.setMaximumWidth(14)

        label_widget = QtWidgets.QLabel(error_info["title"], title_frame)

        title_frame_layout = QtWidgets.QHBoxLayout(title_frame)
        title_frame_layout.addWidget(label_widget, 1)
        title_frame_layout.addWidget(toggle_instance_btn, 0)

        instances_model = QtGui.QStandardItemModel()

        instance_ids = []

        items = []
        context_validation = False
        for error_item in error_info["error_items"]:
            context_validation = error_item.context_validation
            if context_validation:
                toggle_instance_btn.setArrowType(QtCore.Qt.NoArrow)
                instance_ids.append(CONTEXT_ID)
                # Add fake item to have minimum size hint of view widget
                items.append(QtGui.QStandardItem(CONTEXT_LABEL))
                continue

            label = error_item.instance_label
            item = QtGui.QStandardItem(label)
            item.setFlags(
                QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
            )
            item.setData(label, QtCore.Qt.ToolTipRole)
            item.setData(error_item.instance_id, INSTANCE_ID_ROLE)
            items.append(item)
            instance_ids.append(error_item.instance_id)

        if items:
            root_item = instances_model.invisibleRootItem()
            root_item.appendRows(items)

        instances_view = ValidationErrorInstanceList(self)
        instances_view.setModel(instances_model)

        self.setLayoutDirection(QtCore.Qt.LeftToRight)

        view_widget = QtWidgets.QWidget(self)
        view_layout = QtWidgets.QHBoxLayout(view_widget)
        view_layout.setContentsMargins(0, 0, 0, 0)
        view_layout.setSpacing(0)
        view_layout.addSpacing(14)
        view_layout.addWidget(instances_view, 0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(title_frame, 0)
        layout.addWidget(view_widget, 0)
        view_widget.setVisible(False)

        if not context_validation:
            toggle_instance_btn.clicked.connect(self._on_toggle_btn_click)

        title_frame.clicked.connect(self._mouse_release_callback)
        instances_view.selectionModel().selectionChanged.connect(
            self._on_selection_change
        )

        self._title_frame = title_frame

        self._toggle_instance_btn = toggle_instance_btn

        self._view_widget = view_widget

        self._instances_model = instances_model
        self._instances_view = instances_view

        self._context_validation = context_validation

        self._instance_ids = instance_ids
        self._expanded = False

    def sizeHint(self):
        result = super(ValidationErrorTitleWidget, self).sizeHint()
        expected_width = max(
            self._view_widget.minimumSizeHint().width(),
            self._view_widget.sizeHint().width()
        )

        if expected_width < 200:
            expected_width = 200

        if result.width() < expected_width:
            result.setWidth(expected_width)

        return result

    def minimumSizeHint(self):
        return self.sizeHint()

    def _mouse_release_callback(self):
        """Mark this widget as selected on click."""

        self.set_selected(True)

    @property
    def is_selected(self):
        """Is widget marked a selected.

        Returns:
            bool: Item is selected or not.
        """

        return self._selected

    @property
    def id(self):
        return self._title_id

    def _change_style_property(self, selected):
        """Change style of widget based on selection."""

        value = "1" if selected else ""
        self._title_frame.setProperty("selected", value)
        self._title_frame.style().polish(self._title_frame)

    def set_selected(self, selected=None):
        """Change selected state of widget."""

        if selected is None:
            selected = not self._selected

        # Clear instance view selection on deselect
        if not selected:
            self._instances_view.clearSelection()

        # Skip if has same value
        if selected == self._selected:
            return

        self._selected = selected
        self._change_style_property(selected)
        if selected:
            self.selected.emit(self._title_id)
            self._set_expanded(True)

    def _on_toggle_btn_click(self):
        """Show/hide instances list."""

        self._set_expanded()

    def _set_expanded(self, expanded=None):
        if expanded is None:
            expanded = not self._expanded

        elif expanded is self._expanded:
            return

        if expanded and self._context_validation:
            return

        self._expanded = expanded
        self._view_widget.setVisible(expanded)
        if expanded:
            self._toggle_instance_btn.setArrowType(QtCore.Qt.DownArrow)
        else:
            self._toggle_instance_btn.setArrowType(QtCore.Qt.RightArrow)

    def _on_selection_change(self):
        self.instance_changed.emit(self._title_id)

    def get_selected_instances(self):
        if self._context_validation:
            return [CONTEXT_ID]
        sel_model = self._instances_view.selectionModel()
        return [
            index.data(INSTANCE_ID_ROLE)
            for index in sel_model.selectedIndexes()
            if index.isValid()
        ]

    def get_available_instances(self):
        return list(self._instance_ids)


class ValidationArtistMessage(QtWidgets.QWidget):
    def __init__(self, message, parent):
        super(ValidationArtistMessage, self).__init__(parent)

        artist_msg_label = QtWidgets.QLabel(message, self)
        artist_msg_label.setAlignment(QtCore.Qt.AlignCenter)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(
            artist_msg_label, 1, QtCore.Qt.AlignCenter
        )


class ValidationErrorsView(QtWidgets.QWidget):
    selection_changed = QtCore.Signal()

    def __init__(self, parent):
        super(ValidationErrorsView, self).__init__(parent)

        errors_scroll = VerticalScrollArea(self)
        errors_scroll.setWidgetResizable(True)

        errors_widget = QtWidgets.QWidget(errors_scroll)
        errors_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        errors_scroll.setWidget(errors_widget)

        errors_layout = QtWidgets.QVBoxLayout(errors_widget)
        errors_layout.setContentsMargins(0, 0, 0, 0)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(errors_scroll, 1)

        self._errors_widget = errors_widget
        self._errors_layout = errors_layout
        self._title_widgets = {}
        self._previous_select = None

    def _clear(self):
        """Delete all dynamic widgets and hide all wrappers."""

        self._title_widgets = {}
        self._previous_select = None
        while self._errors_layout.count():
            item = self._errors_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def set_errors(self, grouped_error_items):
        """Set errors into context and created titles.

        Args:
            validation_error_report (PublishValidationErrorsReport): Report
                with information about validation errors and publish plugin
                actions.
        """

        self._clear()

        first_id = None
        for title_item in grouped_error_items:
            title_id = title_item["id"]
            if first_id is None:
                first_id = title_id
            widget = ValidationErrorTitleWidget(title_id, title_item, self)
            widget.selected.connect(self._on_select)
            widget.instance_changed.connect(self._on_instance_change)
            self._errors_layout.addWidget(widget)
            self._title_widgets[title_id] = widget

        self._errors_layout.addStretch(1)

        if first_id:
            self._title_widgets[first_id].set_selected(True)
        else:
            self.selection_changed.emit()

        self.updateGeometry()

    def _on_select(self, title_id):
        if self._previous_select:
            if self._previous_select.id == title_id:
                return
            self._previous_select.set_selected(False)

        self._previous_select = self._title_widgets[title_id]
        self.selection_changed.emit()

    def _on_instance_change(self, title_id):
        if self._previous_select and self._previous_select.id != title_id:
            self._title_widgets[title_id].set_selected(True)
        else:
            self.selection_changed.emit()

    def get_selected_items(self):
        if not self._previous_select:
            return None, []

        title_id = self._previous_select.id
        instance_ids = self._previous_select.get_selected_instances()
        if not instance_ids:
            instance_ids = self._previous_select.get_available_instances()
        return title_id, instance_ids


# ----- Publish instance report -----
class _InstanceItem:
    """Publish instance item for report UI.

    Contains only data related to an instance in publishing. Has implemented
    sorting methods and prepares information, e.g. if contains error or
    warnings.
    """

    _attrs = (
        "creator_identifier",
        "family",
        "label",
        "name",
    )

    def __init__(
        self,
        instance_id,
        creator_identifier,
        family,
        name,
        label,
        exists,
        logs,
        errored,
        warned
    ):
        self.id = instance_id
        self.creator_identifier = creator_identifier
        self.family = family
        self.name = name
        self.label = label
        self.exists = exists
        self.logs = logs
        self.errored = errored
        self.warned = warned

    def __eq__(self, other):
        for attr in self._attrs:
            if getattr(self, attr) != getattr(other, attr):
                return False
        return True

    def __ne__(self, other):
        return not self.__eq__(other)

    def __gt__(self, other):
        for attr in self._attrs:
            self_value = getattr(self, attr)
            other_value = getattr(other, attr)
            if self_value == other_value:
                continue
            values = [self_value, other_value]
            values.sort()
            return values[0] == other_value
        return None

    def __lt__(self, other):
        for attr in self._attrs:
            self_value = getattr(self, attr)
            other_value = getattr(other, attr)
            if self_value == other_value:
                continue
            if self_value is None:
                return False
            if other_value is None:
                return True
            values = [self_value, other_value]
            values.sort()
            return values[0] == self_value
        return None

    def __ge__(self, other):
        if self == other:
            return True
        return self.__gt__(other)

    def __le__(self, other):
        if self == other:
            return True
        return self.__lt__(other)

    @classmethod
    def from_report(cls, instance_id, instance_data, logs):
        errored, warned = cls.extract_basic_log_info(logs)

        return cls(
            instance_id,
            instance_data["creator_identifier"],
            instance_data["family"],
            instance_data["name"],
            instance_data["label"],
            instance_data["exists"],
            logs,
            errored,
            warned,
        )

    @classmethod
    def create_context_item(cls, context_label, logs):
        errored, warned = cls.extract_basic_log_info(logs)
        return cls(
            CONTEXT_ID,
            None,
            "",
            CONTEXT_LABEL,
            context_label,
            True,
            logs,
            errored,
            warned
        )

    @staticmethod
    def extract_basic_log_info(logs):
        warned = False
        errored = False
        for log in logs:
            if log["type"] == "error":
                errored = True
            elif log["type"] == "record":
                level_no = log["levelno"]
                if level_no and level_no >= logging.WARNING:
                    warned = True

            if warned and errored:
                break
        return errored, warned


class FamilyGroupLabel(QtWidgets.QWidget):
    def __init__(self, family, parent):
        super(FamilyGroupLabel, self).__init__(parent)

        self.setLayoutDirection(QtCore.Qt.LeftToRight)

        label_widget = QtWidgets.QLabel(family, self)

        line_widget = QtWidgets.QWidget(self)
        line_widget.setObjectName("Separator")
        line_widget.setMinimumHeight(2)
        line_widget.setMaximumHeight(2)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setAlignment(QtCore.Qt.AlignVCenter)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(label_widget, 0)
        main_layout.addWidget(line_widget, 1)


class PublishInstanceCardWidget(BaseClickableFrame):
    selection_requested = QtCore.Signal(str)

    _warning_pix = None
    _error_pix = None
    _success_pix = None
    _in_progress_pix = None

    def __init__(self, instance, icon, publish_finished, parent):
        super(PublishInstanceCardWidget, self).__init__(parent)

        self.setObjectName("CardViewWidget")

        icon_widget = IconValuePixmapLabel(icon, self)
        icon_widget.setObjectName("FamilyIconLabel")

        label_widget = QtWidgets.QLabel(instance.label, self)

        if instance.errored:
            state_pix = self.get_error_pix()
        elif instance.warned:
            state_pix = self.get_warning_pix()
        elif publish_finished:
            state_pix = self.get_success_pix()
        else:
            state_pix = self.get_in_progress_pix()

        state_label = IconValuePixmapLabel(state_pix, self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(10, 7, 10, 7)
        layout.addWidget(icon_widget, 0)
        layout.addWidget(label_widget, 1)
        layout.addWidget(state_label, 0)

        # Change direction -> parent is scroll area where scrolls are on
        #   left side
        self.setLayoutDirection(QtCore.Qt.LeftToRight)

        self._id = instance.id

        self._selected = False

        self._update_style_state()

    @classmethod
    def _prepare_pixes(cls):
        publisher_colors = get_objected_colors("publisher")
        cls._warning_pix = paint_image_with_color(
            get_image("warning"),
            publisher_colors["warning"].get_qcolor()
        )
        cls._error_pix = paint_image_with_color(
            get_image("error"),
            publisher_colors["error"].get_qcolor()
        )
        cls._success_pix = paint_image_with_color(
            get_image("success"),
            publisher_colors["success"].get_qcolor()
        )
        cls._in_progress_pix = paint_image_with_color(
            get_image("success"),
            publisher_colors["progress"].get_qcolor()
        )

    @classmethod
    def get_warning_pix(cls):
        if cls._warning_pix is None:
            cls._prepare_pixes()
        return cls._warning_pix

    @classmethod
    def get_error_pix(cls):
        if cls._error_pix is None:
            cls._prepare_pixes()
        return cls._error_pix

    @classmethod
    def get_success_pix(cls):
        if cls._success_pix is None:
            cls._prepare_pixes()
        return cls._success_pix

    @classmethod
    def get_in_progress_pix(cls):
        if cls._in_progress_pix is None:
            cls._prepare_pixes()
        return cls._in_progress_pix

    @property
    def id(self):
        """Id of card.

        Returns:
            str: Id of item.
        """

        return self._id

    @property
    def is_selected(self):
        """Is card selected.

        Returns:
            bool: Item widget is marked as selected.
        """

        return self._selected

    def set_selected(self, selected):
        """Set card as selected.

        Args:
            selected (bool): Item should be marked as selected.
        """

        if selected == self._selected:
            return
        self._selected = selected
        self._update_style_state()

    def _update_style_state(self):
        state = ""
        if self._selected:
            state = "selected"

        self.setProperty("state", state)
        self.style().polish(self)

    def _mouse_release_callback(self):
        """Trigger selected signal."""

        self.selection_requested.emit(self.id)


class PublishInstancesViewWidget(QtWidgets.QWidget):
    # Sane minimum width of instance cards - size calulated using font metrics
    _min_width_measure_string = 24 * "O"
    selection_changed = QtCore.Signal()

    def __init__(self, controller, parent):
        super(PublishInstancesViewWidget, self).__init__(parent)

        scroll_area = VerticalScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scrollbar_bg = scroll_area.verticalScrollBar().parent()
        if scrollbar_bg:
            scrollbar_bg.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        scroll_area.setViewportMargins(0, 0, 0, 0)

        instance_view = QtWidgets.QWidget(scroll_area)

        scroll_area.setWidget(instance_view)

        instance_layout = QtWidgets.QVBoxLayout(instance_view)
        instance_layout.setContentsMargins(0, 0, 0, 0)
        instance_layout.addStretch(1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll_area, 1)

        self._controller = controller
        self._scroll_area = scroll_area
        self._instance_view = instance_view
        self._instance_layout = instance_layout

        self._context_widget = None

        self._widgets_by_instance_id = {}
        self._group_widgets = []
        self._ordered_widgets = []

        self._explicitly_selected_instance_ids = []

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            self.sizePolicy().verticalPolicy()
        )

    def sizeHint(self):
        """Modify sizeHint based on visibility of scroll bars."""
        # Calculate width hint by content widget and vertical scroll bar
        scroll_bar = self._scroll_area.verticalScrollBar()
        view_size = self._instance_view.sizeHint().width()
        fm = self._instance_view.fontMetrics()
        width = (
            max(view_size, fm.width(self._min_width_measure_string))
            + scroll_bar.sizeHint().width()
        )

        result = super(PublishInstancesViewWidget, self).sizeHint()
        result.setWidth(width)
        return result

    def _get_selected_widgets(self):
        return [
            widget
            for widget in self._ordered_widgets
            if widget.is_selected
        ]

    def get_selected_instance_ids(self):
        return [
            widget.id
            for widget in self._get_selected_widgets()
        ]

    def clear(self):
        """Remove actions from widget."""
        while self._instance_layout.count():
            item = self._instance_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setVisible(False)
                widget.deleteLater()
        self._ordered_widgets = []
        self._group_widgets = []
        self._widgets_by_instance_id = {}

    def update_instances(self, instance_items):
        self.clear()
        identifiers = {
            instance_item.creator_identifier
            for instance_item in instance_items
        }
        identifier_icons = {
            identifier: self._controller.get_creator_icon(identifier)
            for identifier in identifiers
        }

        widgets = []
        group_widgets = []

        publish_finished = (
            self._controller.publish_has_crashed
            or self._controller.publish_has_validation_errors
            or self._controller.publish_has_finished
        )
        instances_by_family = collections.defaultdict(list)
        for instance_item in instance_items:
            if not instance_item.exists:
                continue
            instances_by_family[instance_item.family].append(instance_item)

        sorted_by_family = sorted(
            instances_by_family.items(), key=lambda i: i[0]
        )
        for family, instance_items in sorted_by_family:
            # Only instance without family is context
            if family:
                group_widget = FamilyGroupLabel(family, self._instance_view)
                self._instance_layout.addWidget(group_widget, 0)
                group_widgets.append(group_widget)

            sorted_items = sorted(instance_items, key=lambda i: i.label)
            for instance_item in sorted_items:
                icon = identifier_icons[instance_item.creator_identifier]

                widget = PublishInstanceCardWidget(
                    instance_item, icon, publish_finished, self._instance_view
                )
                widget.selection_requested.connect(self._on_selection_request)
                self._instance_layout.addWidget(widget, 0)

                widgets.append(widget)
                self._widgets_by_instance_id[widget.id] = widget
        self._instance_layout.addStretch(1)
        self._ordered_widgets = widgets
        self._group_widgets = group_widgets

    def _on_selection_request(self, instance_id):
        instance_widget = self._widgets_by_instance_id[instance_id]
        selected_widgets = self._get_selected_widgets()
        if instance_widget in selected_widgets:
            instance_widget.set_selected(False)
        else:
            instance_widget.set_selected(True)
            for widget in selected_widgets:
                widget.set_selected(False)
        self.selection_changed.emit()


class LogIconFrame(QtWidgets.QFrame):
    """Draw log item icon next to message.

    Todos:
        Paint event could be slow, maybe we could cache the image into pixmaps
            so each item does not have to redraw it again.
    """

    info_color = QtGui.QColor("#ffffff")
    error_color = QtGui.QColor("#ff4a4a")
    level_to_color = dict((
        (10, QtGui.QColor("#ff66e8")),
        (20, QtGui.QColor("#66abff")),
        (30, QtGui.QColor("#ffba66")),
        (40, QtGui.QColor("#ff4d58")),
        (50, QtGui.QColor("#ff4f75")),
    ))
    _error_pix = None
    _validation_error_pix = None

    def __init__(self, parent, log_type, log_level, is_validation_error):
        super(LogIconFrame, self).__init__(parent)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self._is_record = log_type == "record"
        self._is_error = log_type == "error"
        self._is_validation_error = bool(is_validation_error)
        self._log_color = self.level_to_color.get(log_level)

    @classmethod
    def get_validation_error_icon(cls):
        if cls._validation_error_pix is None:
            cls._validation_error_pix = get_pixmap("warning")
        return cls._validation_error_pix

    @classmethod
    def get_error_icon(cls):
        if cls._error_pix is None:
            cls._error_pix = get_pixmap("error")
        return cls._error_pix

    def minimumSizeHint(self):
        fm = self.fontMetrics()
        size = fm.height()
        return QtCore.QSize(size, size)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHints(
            QtGui.QPainter.Antialiasing
            | QtGui.QPainter.SmoothPixmapTransform
        )
        painter.setPen(QtCore.Qt.NoPen)
        rect = self.rect()
        new_size = min(rect.width(), rect.height())
        new_rect = QtCore.QRect(1, 1, new_size - 2, new_size - 2)
        if self._is_error:
            if self._is_validation_error:
                error_icon = self.get_validation_error_icon()
            else:
                error_icon = self.get_error_icon()
            scaled_error_icon = error_icon.scaled(
                new_rect.size(),
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )
            painter.drawPixmap(new_rect, scaled_error_icon)

        else:
            if self._is_record:
                color = self._log_color
            else:
                color = QtGui.QColor(255, 255, 255)
            painter.setBrush(color)
            painter.drawEllipse(new_rect)
        painter.end()


class LogItemWidget(QtWidgets.QWidget):
    log_level_to_flag = {
        10: LOG_DEBUG_VISIBLE,
        20: LOG_INFO_VISIBLE,
        30: LOG_WARNING_VISIBLE,
        40: LOG_ERROR_VISIBLE,
        50: LOG_CRITICAL_VISIBLE,
    }

    def __init__(self, log, parent):
        super(LogItemWidget, self).__init__(parent)

        type_flag, level_n = self._get_log_info(log)
        icon_label = LogIconFrame(
            self, log["type"], level_n, log.get("is_validation_error"))
        message_label = QtWidgets.QLabel(log["msg"].rstrip(), self)
        message_label.setObjectName("PublishLogMessage")
        message_label.setTextInteractionFlags(
            QtCore.Qt.TextBrowserInteraction)
        message_label.setCursor(QtGui.QCursor(QtCore.Qt.IBeamCursor))
        message_label.setWordWrap(True)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(8)
        main_layout.addWidget(icon_label, 0)
        main_layout.addWidget(message_label, 1)

        self._type_flag = type_flag
        self._plugin_id = log["plugin_id"]
        self._log_type_filtered = False
        self._plugin_filtered = False

    @property
    def type_flag(self):
        return self._type_flag

    @property
    def plugin_id(self):
        return self._plugin_id

    def _get_log_info(self, log):
        log_type = log["type"]
        if log_type == "error":
            return ERROR_VISIBLE, None

        if log_type != "record":
            return INFO_VISIBLE, None

        level_n = log["levelno"]
        if level_n < 10:
            level_n = 10
        elif level_n % 10 != 0:
            level_n -= (level_n % 10) + 10

        flag = self.log_level_to_flag.get(level_n, LOG_CRITICAL_VISIBLE)
        return flag, level_n

    def _update_visibility(self):
        self.setVisible(
            not self._log_type_filtered
            and not self._plugin_filtered
        )

    def set_log_type_filtered(self, filtered):
        if filtered is self._log_type_filtered:
            return
        self._log_type_filtered = filtered
        self._update_visibility()

    def set_plugin_filtered(self, filtered):
        if filtered is self._plugin_filtered:
            return
        self._plugin_filtered = filtered
        self._update_visibility()


class LogsWithIconsView(QtWidgets.QWidget):
    """Show logs in a grid with 2 columns.

    First column is for icon second is for message.

    Todos:
        Add filtering by type (exception, debug, info, etc.).
    """

    def __init__(self, logs, parent):
        super(LogsWithIconsView, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        logs_layout = QtWidgets.QVBoxLayout(self)
        logs_layout.setContentsMargins(0, 0, 0, 0)
        logs_layout.setSpacing(4)

        widgets_by_flag = collections.defaultdict(list)
        widgets_by_plugins_id = collections.defaultdict(list)

        for log in logs:
            widget = LogItemWidget(log, self)
            widgets_by_flag[widget.type_flag].append(widget)
            widgets_by_plugins_id[widget.plugin_id].append(widget)
            logs_layout.addWidget(widget, 0)

        self._widgets_by_flag = widgets_by_flag
        self._widgets_by_plugins_id = widgets_by_plugins_id

        self._visibility_by_flags = {
            LOG_DEBUG_VISIBLE: True,
            LOG_INFO_VISIBLE: True,
            LOG_WARNING_VISIBLE: True,
            LOG_ERROR_VISIBLE: True,
            LOG_CRITICAL_VISIBLE: True,
            ERROR_VISIBLE: True,
            INFO_VISIBLE: True,
        }
        self._flags_filter = sum(self._visibility_by_flags.keys())
        self._plugin_ids_filter = None

    def _update_flags_filtering(self):
        for flag in (
            LOG_DEBUG_VISIBLE,
            LOG_INFO_VISIBLE,
            LOG_WARNING_VISIBLE,
            LOG_ERROR_VISIBLE,
            LOG_CRITICAL_VISIBLE,
            ERROR_VISIBLE,
            INFO_VISIBLE,
        ):
            visible = (self._flags_filter & flag) != 0
            if visible is not self._visibility_by_flags[flag]:
                self._visibility_by_flags[flag] = visible
                for widget in self._widgets_by_flag[flag]:
                    widget.set_log_type_filtered(not visible)

    def _update_plugin_filtering(self):
        if self._plugin_ids_filter is None:
            for widgets in self._widgets_by_plugins_id.values():
                for widget in widgets:
                    widget.set_plugin_filtered(False)

        else:
            for plugin_id, widgets in self._widgets_by_plugins_id.items():
                filtered = plugin_id not in self._plugin_ids_filter
                for widget in widgets:
                    widget.set_plugin_filtered(filtered)

    def set_log_filters(self, visibility_filter, plugin_ids):
        if self._flags_filter != visibility_filter:
            self._flags_filter = visibility_filter
            self._update_flags_filtering()

        if self._plugin_ids_filter != plugin_ids:
            if plugin_ids is not None:
                plugin_ids = set(plugin_ids)
            self._plugin_ids_filter = plugin_ids
            self._update_plugin_filtering()


class InstanceLogsWidget(QtWidgets.QWidget):
    """Widget showing logs of one publish instance.

    Args:
        instance (_InstanceItem): Item of instance used as data source.
        parent (QtWidgets.QWidget): Parent widget.
    """

    def __init__(self, instance, parent):
        super(InstanceLogsWidget, self).__init__(parent)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        label_widget = QtWidgets.QLabel(instance.label, self)
        label_widget.setObjectName("PublishInstanceLogsLabel")
        logs_grid = LogsWithIconsView(instance.logs, self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label_widget, 0)
        layout.addWidget(logs_grid, 0)

        self._logs_grid = logs_grid

    def set_log_filters(self, visibility_filter, plugin_ids):
        """Change logs filter.

        Args:
            visibility_filter (int): Number contained of flags for each log
                type and level.
            plugin_ids (Iterable[str]): Plugin ids to which are logs filtered.
        """

        self._logs_grid.set_log_filters(visibility_filter, plugin_ids)


class InstancesLogsView(QtWidgets.QFrame):
    """Publish instances logs view widget."""

    def __init__(self, parent):
        super(InstancesLogsView, self).__init__(parent)
        self.setObjectName("InstancesLogsView")

        scroll_area = QtWidgets.QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        scroll_area.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        scrollbar_bg = scroll_area.verticalScrollBar().parent()
        if scrollbar_bg:
            scrollbar_bg.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        content_wrap_widget = QtWidgets.QWidget(scroll_area)
        content_wrap_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        content_widget = QtWidgets.QWidget(content_wrap_widget)
        content_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        content_layout = QtWidgets.QVBoxLayout(content_widget)
        content_layout.setSpacing(15)

        scroll_area.setWidget(content_wrap_widget)

        content_wrap_layout = QtWidgets.QVBoxLayout(content_wrap_widget)
        content_wrap_layout.setContentsMargins(0, 0, 0, 0)
        content_wrap_layout.addWidget(content_widget, 0)
        content_wrap_layout.addStretch(1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll_area, 1)

        self._visible_filters = (
            LOG_INFO_VISIBLE
            | LOG_WARNING_VISIBLE
            | LOG_ERROR_VISIBLE
            | LOG_CRITICAL_VISIBLE
            | ERROR_VISIBLE
            | INFO_VISIBLE
        )

        self._content_widget = content_widget
        self._content_layout = content_layout

        self._instances_order = []
        self._instances_by_id = {}
        self._views_by_instance_id = {}
        self._is_showed = False
        self._clear_needed = False
        self._update_needed = False
        self._instance_ids_filter = []
        self._plugin_ids_filter = None

    def showEvent(self, event):
        super(InstancesLogsView, self).showEvent(event)
        self._is_showed = True
        self._update_instances()

    def hideEvent(self, event):
        super(InstancesLogsView, self).hideEvent(event)
        self._is_showed = False

    def closeEvent(self, event):
        super(InstancesLogsView, self).closeEvent(event)
        self._is_showed = False

    def _update_instances(self):
        if not self._is_showed:
            return

        if self._clear_needed:
            self._clear_widgets()
            self._clear_needed = False

        if not self._update_needed:
            return
        self._update_needed = False

        instance_ids = self._instance_ids_filter
        to_hide = set()
        if not instance_ids:
            instance_ids = self._instances_by_id
        else:
            to_hide = set(self._instances_by_id) - set(instance_ids)

        for instance_id in instance_ids:
            widget = self._views_by_instance_id.get(instance_id)
            if widget is None:
                instance = self._instances_by_id[instance_id]
                widget = InstanceLogsWidget(instance, self._content_widget)
                self._views_by_instance_id[instance_id] = widget
                self._content_layout.addWidget(widget, 0)

            widget.setVisible(True)
            widget.set_log_filters(
                self._visible_filters, self._plugin_ids_filter
            )

        for instance_id in to_hide:
            widget = self._views_by_instance_id.get(instance_id)
            if widget is not None:
                widget.setVisible(False)

    def _clear_widgets(self):
        """Remove all widgets from layout and from cache."""

        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setVisible(False)
                widget.deleteLater()
        self._views_by_instance_id = {}

    def update_instances(self, instances):
        """Update publish instance from report.

        Args:
            instances (list[_InstanceItem]): Instance data from report.
        """

        self._instances_order = [
            instance.id for instance in instances
        ]
        self._instances_by_id = {
            instance.id: instance
            for instance in instances
        }
        self._instance_ids_filter = []
        self._plugin_ids_filter = None
        self._clear_needed = True
        self._update_needed = True
        self._update_instances()

    def set_instances_filter(self, instance_ids=None):
        """Set instance filter.

        Args:
            instance_ids (Optional[list[str]]): List of instances to keep
                visible. Pass empty list to hide all items.
        """

        self._instance_ids_filter = instance_ids
        self._update_needed = True
        self._update_instances()

    def set_plugins_filter(self, plugin_ids=None):
        if self._plugin_ids_filter == plugin_ids:
            return
        self._plugin_ids_filter = plugin_ids
        self._update_needed = True
        self._update_instances()


class CrashWidget(QtWidgets.QWidget):
    """Widget shown when publishing crashes.

    Contains only minimal information for artist with easy access to report
    actions.
    """

    def __init__(self, controller, parent):
        super(CrashWidget, self).__init__(parent)

        main_label = QtWidgets.QLabel("This is not your fault", self)
        main_label.setAlignment(QtCore.Qt.AlignCenter)
        main_label.setObjectName("PublishCrashMainLabel")

        report_label = QtWidgets.QLabel(
            (
                "Please report the error to your pipeline support"
                " using one of the options below."
            ),
            self
        )
        report_label.setAlignment(QtCore.Qt.AlignCenter)
        report_label.setWordWrap(True)
        report_label.setObjectName("PublishCrashReportLabel")

        btns_widget = QtWidgets.QWidget(self)
        copy_clipboard_btn = QtWidgets.QPushButton(
            "Copy to clipboard", btns_widget)
        save_to_disk_btn = QtWidgets.QPushButton(
            "Save to disk", btns_widget)

        btns_layout = QtWidgets.QHBoxLayout(btns_widget)
        btns_layout.addStretch(1)
        btns_layout.addWidget(copy_clipboard_btn, 0)
        btns_layout.addSpacing(20)
        btns_layout.addWidget(save_to_disk_btn, 0)
        btns_layout.addStretch(1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addStretch(1)
        layout.addWidget(main_label, 0)
        layout.addSpacing(20)
        layout.addWidget(report_label, 0)
        layout.addSpacing(20)
        layout.addWidget(btns_widget, 0)
        layout.addStretch(2)

        copy_clipboard_btn.clicked.connect(self._on_copy_to_clipboard)
        save_to_disk_btn.clicked.connect(self._on_save_to_disk_click)

        self._controller = controller

    def _on_copy_to_clipboard(self):
        self._controller.event_system.emit(
            "copy_report.request", {}, "report_page")

    def _on_save_to_disk_click(self):
        self._controller.event_system.emit(
            "export_report.request", {}, "report_page")


class ErrorDetailsWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(ErrorDetailsWidget, self).__init__(parent)

        inputs_widget = QtWidgets.QWidget(self)
        # Error 'Description' input
        error_description_input = ExpandingTextEdit(inputs_widget)
        error_description_input.setObjectName("InfoText")
        error_description_input.setTextInteractionFlags(
            QtCore.Qt.TextBrowserInteraction
        )

        # Error 'Details' widget -> Collapsible
        error_details_widget = QtWidgets.QWidget(inputs_widget)

        error_details_top = ClickableFrame(error_details_widget)

        error_details_expand_btn = ClassicExpandBtn(error_details_top)
        error_details_expand_label = QtWidgets.QLabel(
            "Details", error_details_top)

        line_widget = SeparatorWidget(1, parent=error_details_top)

        error_details_top_l = QtWidgets.QHBoxLayout(error_details_top)
        error_details_top_l.setContentsMargins(0, 0, 10, 0)
        error_details_top_l.addWidget(error_details_expand_btn, 0)
        error_details_top_l.addWidget(error_details_expand_label, 0)
        error_details_top_l.addWidget(line_widget, 1)

        error_details_input = ExpandingTextEdit(error_details_widget)
        error_details_input.setObjectName("InfoText")
        error_details_input.setTextInteractionFlags(
            QtCore.Qt.TextBrowserInteraction
        )
        error_details_input.setVisible(not error_details_expand_btn.collapsed)

        error_details_layout = QtWidgets.QVBoxLayout(error_details_widget)
        error_details_layout.setContentsMargins(0, 0, 0, 0)
        error_details_layout.addWidget(error_details_top, 0)
        error_details_layout.addWidget(error_details_input, 0)
        error_details_layout.addStretch(1)

        # Description and Details layout
        inputs_layout = QtWidgets.QVBoxLayout(inputs_widget)
        inputs_layout.setContentsMargins(0, 0, 0, 0)
        inputs_layout.setSpacing(10)
        inputs_layout.addWidget(error_description_input, 0)
        inputs_layout.addWidget(error_details_widget, 1)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(inputs_widget, 1)

        error_details_top.clicked.connect(self._on_detail_toggle)

        self._error_details_widget = error_details_widget
        self._error_description_input = error_description_input
        self._error_details_expand_btn = error_details_expand_btn
        self._error_details_input = error_details_input

    def _on_detail_toggle(self):
        self._error_details_expand_btn.set_collapsed()
        self._error_details_input.setVisible(
            not self._error_details_expand_btn.collapsed)

    def set_error_item(self, error_item):
        detail = ""
        description = ""
        if error_item:
            description = error_item.description or description
            detail = error_item.detail or detail

        if commonmark:
            self._error_description_input.setHtml(
                commonmark.commonmark(description)
            )
            self._error_details_input.setHtml(
                commonmark.commonmark(detail)
            )

        elif hasattr(self._error_details_input, "setMarkdown"):
            self._error_description_input.setMarkdown(description)
            self._error_details_input.setMarkdown(detail)

        else:
            self._error_description_input.setText(description)
            self._error_details_input.setText(detail)

        self._error_details_widget.setVisible(bool(detail))


class ReportsWidget(QtWidgets.QWidget):
    """
        # Crash layout
        ┌──────┬─────────┬─────────┐
        │Views │ Logs    │ Details │
        │      │         │         │
        │      │         │         │
        └──────┴─────────┴─────────┘
        # Success layout
        ┌──────┬───────────────────┐
        │View  │ Logs              │
        │      │                   │
        │      │                   │
        └──────┴───────────────────┘
        # Validation errors layout
        ┌──────┬─────────┬─────────┐
        │Views │ Actions │         │
        │      ├─────────┤ Details │
        │      │ Logs    │         │
        │      │         │         │
        └──────┴─────────┴─────────┘
    """

    def __init__(self, controller, parent):
        super(ReportsWidget, self).__init__(parent)

        # Instances view
        views_widget = QtWidgets.QWidget(self)

        instances_view = PublishInstancesViewWidget(controller, views_widget)

        validation_error_view = ValidationErrorsView(views_widget)

        views_layout = QtWidgets.QStackedLayout(views_widget)
        views_layout.setContentsMargins(0, 0, 0, 0)
        views_layout.addWidget(instances_view)
        views_layout.addWidget(validation_error_view)

        views_layout.setCurrentWidget(instances_view)

        # Error description with actions and optional detail
        details_widget = QtWidgets.QFrame(self)
        details_widget.setObjectName("PublishInstancesDetails")

        # Actions widget
        actions_widget = ValidateActionsWidget(controller, details_widget)

        pages_widget = QtWidgets.QWidget(details_widget)

        # Logs view
        logs_view = InstancesLogsView(pages_widget)

        # Validation details
        # Description and details inputs are in scroll
        # - single scroll for both inputs, they are forced to not use theirs
        detail_inputs_spacer = QtWidgets.QWidget(pages_widget)
        detail_inputs_spacer.setMinimumWidth(30)
        detail_inputs_spacer.setMaximumWidth(30)

        detail_input_scroll = QtWidgets.QScrollArea(pages_widget)

        detail_inputs_widget = ErrorDetailsWidget(detail_input_scroll)
        detail_inputs_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        detail_input_scroll.setWidget(detail_inputs_widget)
        detail_input_scroll.setWidgetResizable(True)
        detail_input_scroll.setViewportMargins(0, 0, 0, 0)

        # Crash information
        crash_widget = CrashWidget(controller, details_widget)

        # Layout pages
        pages_layout = QtWidgets.QHBoxLayout(pages_widget)
        pages_layout.setContentsMargins(0, 0, 0, 0)
        pages_layout.addWidget(logs_view, 1)
        pages_layout.addWidget(detail_inputs_spacer, 0)
        pages_layout.addWidget(detail_input_scroll, 1)
        pages_layout.addWidget(crash_widget, 1)

        details_layout = QtWidgets.QVBoxLayout(details_widget)
        margins = details_layout.contentsMargins()
        margins.setTop(margins.top() * 2)
        margins.setBottom(margins.bottom() * 2)
        details_layout.setContentsMargins(margins)
        details_layout.setSpacing(margins.top())
        details_layout.addWidget(actions_widget, 0)
        details_layout.addWidget(pages_widget, 1)

        content_layout = QtWidgets.QHBoxLayout(self)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(views_widget, 0)
        content_layout.addWidget(details_widget, 1)

        instances_view.selection_changed.connect(self._on_instance_selection)
        validation_error_view.selection_changed.connect(
            self._on_error_selection)

        self._views_layout = views_layout
        self._instances_view = instances_view
        self._validation_error_view = validation_error_view

        self._actions_widget = actions_widget
        self._detail_inputs_widget = detail_inputs_widget
        self._logs_view = logs_view
        self._detail_inputs_spacer = detail_inputs_spacer
        self._detail_input_scroll = detail_input_scroll
        self._crash_widget = crash_widget

        self._controller = controller

        self._validation_errors_by_id = {}

    def _get_instance_items(self):
        report = self._controller.get_publish_report()
        context_label = report["context"]["label"] or CONTEXT_LABEL
        instances_by_id = report["instances"]
        plugins_info = report["plugins_data"]
        logs_by_instance_id = collections.defaultdict(list)
        for plugin_info in plugins_info:
            plugin_id = plugin_info["id"]
            for instance_info in plugin_info["instances_data"]:
                instance_id = instance_info["id"] or CONTEXT_ID
                for log in instance_info["logs"]:
                    log["plugin_id"] = plugin_id
                logs_by_instance_id[instance_id].extend(instance_info["logs"])

        context_item = _InstanceItem.create_context_item(
            context_label, logs_by_instance_id[CONTEXT_ID])
        instance_items = [
            _InstanceItem.from_report(
                instance_id, instance, logs_by_instance_id[instance_id]
            )
            for instance_id, instance in instances_by_id.items()
            if instance["exists"]
        ]
        instance_items.sort()
        instance_items.insert(0, context_item)
        return instance_items

    def update_data(self):
        view = self._instances_view
        validation_error_mode = False
        if (
            not self._controller.publish_has_crashed
            and self._controller.publish_has_validation_errors
        ):
            view = self._validation_error_view
            validation_error_mode = True

        self._actions_widget.set_visible_mode(validation_error_mode)
        self._detail_inputs_spacer.setVisible(validation_error_mode)
        self._detail_input_scroll.setVisible(validation_error_mode)
        self._views_layout.setCurrentWidget(view)

        self._crash_widget.setVisible(self._controller.publish_has_crashed)
        self._logs_view.setVisible(not self._controller.publish_has_crashed)

        # Instance view & logs update
        instance_items = self._get_instance_items()
        self._instances_view.update_instances(instance_items)
        self._logs_view.update_instances(instance_items)

        # Validation errors
        validation_errors = self._controller.get_validation_errors()
        grouped_error_items = validation_errors.group_items_by_title()

        validation_errors_by_id = {
            title_item["id"]: title_item
            for title_item in grouped_error_items
        }

        self._validation_errors_by_id = validation_errors_by_id
        self._validation_error_view.set_errors(grouped_error_items)

    def _on_instance_selection(self):
        instance_ids = self._instances_view.get_selected_instance_ids()
        self._logs_view.set_instances_filter(instance_ids)

    def _on_error_selection(self):
        title_id, instance_ids = (
            self._validation_error_view.get_selected_items())
        error_info = self._validation_errors_by_id.get(title_id)
        if error_info is None:
            self._actions_widget.set_error_info(None)
            self._detail_inputs_widget.set_error_item(None)
            return

        self._logs_view.set_instances_filter(instance_ids)
        self._logs_view.set_plugins_filter([error_info["plugin_id"]])

        match_error_item = None
        for error_item in error_info["error_items"]:
            instance_id = error_item.instance_id or CONTEXT_ID
            if instance_id in instance_ids:
                match_error_item = error_item
                break

        self._actions_widget.set_error_info(error_info)
        self._detail_inputs_widget.set_error_item(match_error_item)


class ReportPageWidget(QtWidgets.QFrame):
    """Widgets showing report for artis.

    There are 5 possible states:
    1. Publishing did not start yet.         > Only label.
    2. Publishing is paused.                ┐
    3. Publishing successfully finished.    │> Instances with logs.
    4. Publishing crashed.                  ┘
    5. Crashed because of validation error.  > Errors with logs.

    This widget is shown if validation errors happened during validation part.

    Shows validation error titles with instances on which they happened
    and validation error detail with possible actions (repair).
    """

    def __init__(self, controller, parent):
        super(ReportPageWidget, self).__init__(parent)

        header_label = QtWidgets.QLabel(self)
        header_label.setAlignment(QtCore.Qt.AlignCenter)
        header_label.setObjectName("PublishReportHeader")

        publish_instances_widget = ReportsWidget(controller, self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(header_label, 0)
        layout.addWidget(publish_instances_widget, 0)

        controller.event_system.add_callback(
            "publish.process.started", self._on_publish_start
        )
        controller.event_system.add_callback(
            "publish.reset.finished", self._on_publish_reset
        )
        controller.event_system.add_callback(
            "publish.process.stopped", self._on_publish_stop
        )

        self._header_label = header_label
        self._publish_instances_widget = publish_instances_widget

        self._controller = controller

    def _update_label(self):
        if not self._controller.publish_has_started:
            # This probably never happen when this widget is visible
            header_label = "Nothing to report until you run publish"
        elif self._controller.publish_has_crashed:
            header_label = "Publish error report"
        elif self._controller.publish_has_validation_errors:
            header_label = "Publish validation report"
        elif self._controller.publish_has_finished:
            header_label = "Publish success report"
        else:
            header_label = "Publish report"
        self._header_label.setText(header_label)

    def _update_state(self):
        self._update_label()
        publish_started = self._controller.publish_has_started
        self._publish_instances_widget.setVisible(publish_started)
        if publish_started:
            self._publish_instances_widget.update_data()

        self.updateGeometry()

    def _on_publish_start(self):
        self._update_state()

    def _on_publish_reset(self):
        self._update_state()

    def _on_publish_stop(self):
        self._update_state()
