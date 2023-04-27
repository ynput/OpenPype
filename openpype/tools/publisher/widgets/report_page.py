# -*- coding: utf-8 -*-
import collections
import logging

try:
    import commonmark
except Exception:
    commonmark = None

from qtpy import QtWidgets, QtCore, QtGui

from openpype.tools.utils import BaseClickableFrame, ClickableFrame
from .widgets import (
    IconValuePixmapLabel,
    get_pixmap,
)
from ..constants import (
    INSTANCE_ID_ROLE,
    CONTEXT_ID,
    CONTEXT_LABEL,
)


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

    selected = QtCore.Signal(int)
    instance_changed = QtCore.Signal(int)

    def __init__(self, index, error_info, parent):
        super(ValidationErrorTitleWidget, self).__init__(parent)

        self._index = index
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

        help_text_by_instance_id = {}

        items = []
        context_validation = False
        for error_item in error_info["error_items"]:
            context_validation = error_item.context_validation
            if context_validation:
                toggle_instance_btn.setArrowType(QtCore.Qt.NoArrow)
                description = self._prepare_description(error_item)
                help_text_by_instance_id[None] = description
                # Add fake item to have minimum size hint of view widget
                items.append(QtGui.QStandardItem("Context"))
                continue

            label = error_item.instance_label
            item = QtGui.QStandardItem(label)
            item.setFlags(
                QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
            )
            item.setData(label, QtCore.Qt.ToolTipRole)
            item.setData(error_item.instance_id, INSTANCE_ID_ROLE)
            items.append(item)
            description = self._prepare_description(error_item)
            help_text_by_instance_id[error_item.instance_id] = description

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
            self._on_seleciton_change
        )

        self._title_frame = title_frame

        self._toggle_instance_btn = toggle_instance_btn

        self._view_widget = view_widget

        self._instances_model = instances_model
        self._instances_view = instances_view

        self._context_validation = context_validation
        self._help_text_by_instance_id = help_text_by_instance_id

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

    def _prepare_description(self, error_item):
        """Prepare description text for detail intput.

        Args:
            error_item (ValidationErrorItem): Item which hold information about
                validation error.

        Returns:
            str: Prepared detailed description.
        """

        dsc = error_item.description
        detail = error_item.detail
        if detail:
            dsc += "<br/><br/>{}".format(detail)

        description = dsc
        if commonmark:
            description = commonmark.commonmark(dsc)
        return description

    def _mouse_release_callback(self):
        """Mark this widget as selected on click."""

        self.set_selected(True)

    def current_description_text(self):
        if self._context_validation:
            return self._help_text_by_instance_id[None]
        index = self._instances_view.currentIndex()
        # TODO make sure instance is selected
        if not index.isValid():
            index = self._instances_model.index(0, 0)

        indence_id = index.data(INSTANCE_ID_ROLE)
        return self._help_text_by_instance_id[indence_id]

    @property
    def is_selected(self):
        """Is widget marked a selected.

        Returns:
            bool: Item is selected or not.
        """

        return self._selected

    @property
    def index(self):
        """Widget's index set by parent.

        Returns:
            int: Index of widget.
        """

        return self._index

    def set_index(self, index):
        """Set index of widget (called by parent).

        Args:
            int: New index of widget.
        """

        self._index = index

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
            self.selected.emit(self._index)
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

    def _on_seleciton_change(self):
        sel_model = self._instances_view.selectionModel()
        if sel_model.selectedIndexes():
            self.instance_changed.emit(self._index)


class ActionButton(BaseClickableFrame):
    """Plugin's action callback button.

    Action may have label or icon or both.

    Args:
        plugin_action_item (PublishPluginActionItem): Action item that can be
            triggered by it's id.
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
        content_layout = QtWidgets.QVBoxLayout(content_widget)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(content_widget)

        self._controller = controller
        self._content_widget = content_widget
        self._content_layout = content_layout
        self._actions_mapping = {}

    def clear(self):
        """Remove actions from widget."""
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setVisible(False)
                widget.deleteLater()
        self._actions_mapping = {}

    def set_error_item(self, error_item):
        """Set selected plugin and show it's actions.

        Clears current actions from widget and recreate them from the plugin.

        Args:
            Dict[str, Any]: Object holding error items, title and possible
                actions to run.
        """

        self.clear()

        if not error_item:
            self.setVisible(False)
            return

        plugin_action_items = error_item["plugin_action_items"]
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

        if self._content_layout.count() > 0:
            self.setVisible(True)
            self._content_layout.addStretch(1)
        else:
            self.setVisible(False)

    def _on_action_click(self, plugin_id, action_id):
        self._controller.run_action(plugin_id, action_id)


class VerticallScrollArea(QtWidgets.QScrollArea):
    """Scroll area for validation error titles.

    The biggest difference is that the scroll area has scroll bar on left side
    and resize of content will also resize scrollarea itself.

    Resize if deferred by 100ms because at the moment of resize are not yet
    propagated sizes and visibility of scroll bars.
    """

    def __init__(self, *args, **kwargs):
        super(VerticallScrollArea, self).__init__(*args, **kwargs)

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

        super(VerticallScrollArea, self).setVerticalScrollBar(widget)
        if widget:
            widget.installEventFilter(self)

    def setWidget(self, widget):
        old_widget = self.widget()
        if old_widget:
            old_widget.removeEventFilter(self)

        super(VerticallScrollArea, self).setWidget(widget)
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
        return super(VerticallScrollArea, self).eventFilter(obj, event)


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


class ValidationsWidget(QtWidgets.QFrame):
    """Widgets showing validation error.

    This widget is shown if validation error/s happened during validation part.

    Shows validation error titles with instances on which happened and
    validation error detail with possible actions (repair).
    """

    def __init__(self, controller, parent):
        super(ValidationsWidget, self).__init__(parent)

        content_widget = QtWidgets.QWidget(self)

        errors_scroll = VerticallScrollArea(content_widget)
        errors_scroll.setWidgetResizable(True)

        errors_widget = QtWidgets.QWidget(errors_scroll)
        errors_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        errors_layout = QtWidgets.QVBoxLayout(errors_widget)
        errors_layout.setContentsMargins(0, 0, 0, 0)

        errors_scroll.setWidget(errors_widget)

        error_details_frame = QtWidgets.QFrame(content_widget)
        error_details_input = QtWidgets.QTextEdit(error_details_frame)
        error_details_input.setObjectName("InfoText")
        error_details_input.setTextInteractionFlags(
            QtCore.Qt.TextBrowserInteraction
        )

        actions_widget = ValidateActionsWidget(controller, content_widget)
        actions_widget.setMinimumWidth(140)

        error_details_layout = QtWidgets.QHBoxLayout(error_details_frame)
        error_details_layout.addWidget(error_details_input, 1)
        error_details_layout.addWidget(actions_widget, 0)

        content_layout = QtWidgets.QHBoxLayout(content_widget)
        content_layout.setSpacing(0)
        content_layout.setContentsMargins(0, 0, 0, 0)

        content_layout.addWidget(errors_scroll, 0)
        content_layout.addWidget(error_details_frame, 1)

        top_label = QtWidgets.QLabel(
            "Publish validation report", content_widget
        )
        top_label.setObjectName("PublishInfoMainLabel")
        top_label.setAlignment(QtCore.Qt.AlignCenter)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(top_label, 0)
        main_layout.addWidget(content_widget, 1)

        self._top_label = top_label
        self._errors_widget = errors_widget
        self._errors_layout = errors_layout
        self._error_details_frame = error_details_frame
        self._error_details_input = error_details_input
        self._actions_widget = actions_widget

        self._title_widgets = {}
        self._error_info = {}
        self._previous_select = None

        self._controller = controller

    def clear(self):
        """Delete all dynamic widgets and hide all wrappers."""
        self._title_widgets = {}
        self._error_info = {}
        self._previous_select = None
        while self._errors_layout.count():
            item = self._errors_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self._top_label.setVisible(False)
        self._error_details_frame.setVisible(False)
        self._errors_widget.setVisible(False)
        self._actions_widget.setVisible(False)

    def _set_errors(self, validation_error_report):
        """Set errors into context and created titles.

        Args:
            validation_error_report (PublishValidationErrorsReport): Report
                with information about validation errors and publish plugin
                actions.
        """

        self.clear()
        if not validation_error_report:
            return

        self._top_label.setVisible(True)
        self._error_details_frame.setVisible(True)
        self._errors_widget.setVisible(True)

        grouped_error_items = validation_error_report.group_items_by_title()
        for idx, error_info in enumerate(grouped_error_items):
            widget = ValidationErrorTitleWidget(idx, error_info, self)
            widget.selected.connect(self._on_select)
            widget.instance_changed.connect(self._on_instance_change)
            self._errors_layout.addWidget(widget)
            self._title_widgets[idx] = widget
            self._error_info[idx] = error_info

        self._errors_layout.addStretch(1)

        if self._title_widgets:
            self._title_widgets[0].set_selected(True)

        self.updateGeometry()

    def update_data(self):
        validation_errors = self._controller.get_validation_errors()
        self._set_errors(validation_errors)

    def _on_select(self, index):
        if self._previous_select:
            if self._previous_select.index == index:
                return
            self._previous_select.set_selected(False)

        self._previous_select = self._title_widgets[index]

        error_item = self._error_info[index]

        self._actions_widget.set_error_item(error_item)

        self._update_description()

    def _on_instance_change(self, index):
        if self._previous_select and self._previous_select.index != index:
            self._title_widgets[index].set_selected(True)
        else:
            self._update_description()

    def _update_description(self):
        description = self._previous_select.current_description_text()
        if commonmark:
            html = commonmark.commonmark(description)
            self._error_details_input.setHtml(html)
        elif hasattr(self._error_details_input, "setMarkdown"):
            self._error_details_input.setMarkdown(description)
        else:
            self._error_details_input.setText(description)


# ----- Publish instance report -----
class _InstanceItem:
    """Publish instance item for report UI.

    Contains only data related to an instance in publishing. Has implemented
    sorting methods and prepares information, e.g. if contains error or
    warnings.
    """

    _attrs = (
        "family",
        "label",
        "name",
    )

    def __init__(
        self, instance_id, family, name, label, exists, logs, errored, warned
    ):
        self.id = instance_id
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


class PublishInstanceCardWidget(BaseClickableFrame):
    selection_requested = QtCore.Signal(str)

    def __init__(self, instance, parent):
        super(PublishInstanceCardWidget, self).__init__(parent)

        self.setObjectName("PublishInstanceCard")

        icon_widget = QtWidgets.QLabel(self)
        label_widget = QtWidgets.QLabel(instance.label, self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(icon_widget, 0)
        layout.addWidget(label_widget, 1)

        # Change direction -> parent is scroll area where scrolls are on
        #   left side
        self.setLayoutDirection(QtCore.Qt.LeftToRight)

        self._id = instance.id

        self._selected = False

        self._update_style_state()

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

    def __init__(self, parent):
        super(PublishInstancesViewWidget, self).__init__(parent)

        scroll_area = VerticallScrollArea(self)
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

        self._scroll_area = scroll_area
        self._instance_view = instance_view
        self._instance_layout = instance_layout

        self._context_widget = None

        self._widgets_by_instance_id = {}
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
        self._widgets_by_instance_id = {}

    def update_instances(self, instance_items):
        self.clear()
        widgets = [
            PublishInstanceCardWidget(instance_item, self._instance_view)
            for instance_item in instance_items
        ]
        for widget in widgets:
            widget.selection_requested.connect(self._on_selection_request)
            self._widgets_by_instance_id[widget.id] = widget
            self._instance_layout.addWidget(widget, 0)
        self._instance_layout.addStretch(1)
        self._ordered_widgets = widgets

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

    def __init__(self, parent, log_type, log_level=None):
        super(LogIconFrame, self).__init__(parent)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        self._is_record = log_type == "record"
        self._is_error = log_type == "error"
        self._log_color = self.level_to_color.get(log_level)

    @classmethod
    def get_error_icon(cls):
        if cls._error_pix is None:
            cls._error_pix = get_pixmap("warning")
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
        if self._is_record:
            painter.setBrush(self._log_color)
            painter.drawEllipse(new_rect)
        elif self._is_error:
            error_icon = self.get_error_icon()
            scaled_error_icon = error_icon.scaled(
                new_rect.size(),
                QtCore.Qt.KeepAspectRatio,
                QtCore.Qt.SmoothTransformation
            )
            painter.drawPixmap(new_rect, scaled_error_icon)
        else:
            painter.setBrush(QtGui.QColor(255, 255, 255))
            painter.drawEllipse(new_rect)
        painter.end()


class LogsGridView(QtWidgets.QWidget):
    """Show logs in a grid with 2 columns.

    First column is for icon second is for message.

    Todos:
        Add filtering by type (exception, debug, info, etc.).
    """

    log_level_to_flag = {
        10: LOG_DEBUG_VISIBLE,
        20: LOG_INFO_VISIBLE,
        30: LOG_WARNING_VISIBLE,
        40: LOG_ERROR_VISIBLE,
        50: LOG_CRITICAL_VISIBLE,
    }

    def __init__(self, logs, parent):
        super(LogsGridView, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        logs_layout = QtWidgets.QGridLayout(self)
        logs_layout.setContentsMargins(0, 0, 0, 0)
        logs_layout.setHorizontalSpacing(4)
        logs_layout.setVerticalSpacing(2)

        widgets_by_flag = collections.defaultdict(list)

        for idx, log in enumerate(logs):
            type_flag, level_n = self._get_log_info(log)
            icon_label = LogIconFrame(self, log["type"], level_n)
            message_label = QtWidgets.QLabel(log["msg"], self)
            message_label.setObjectName("PublishLogMessage")
            message_label.setTextInteractionFlags(
                QtCore.Qt.TextBrowserInteraction)
            message_label.setCursor(QtGui.QCursor(QtCore.Qt.IBeamCursor))
            message_label.setWordWrap(True)
            logs_layout.addWidget(icon_label, idx, 0, 1, 1)
            logs_layout.addWidget(message_label, idx, 1, 1, 1)
            widgets_by_flag[type_flag].append(icon_label)
            widgets_by_flag[type_flag].append(message_label)

        logs_layout.setColumnStretch(0, 0)
        logs_layout.setColumnStretch(1, 1)

        self._widgets_by_flag = widgets_by_flag
        self._visibility_by_flags = {
            LOG_DEBUG_VISIBLE: True,
            LOG_INFO_VISIBLE: True,
            LOG_WARNING_VISIBLE: True,
            LOG_ERROR_VISIBLE: True,
            LOG_CRITICAL_VISIBLE: True,
            ERROR_VISIBLE: True,
            INFO_VISIBLE: True,
        }
        self._visibility = sum(self._visibility_by_flags.keys())

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
        for flag in (
            LOG_DEBUG_VISIBLE,
            LOG_INFO_VISIBLE,
            LOG_WARNING_VISIBLE,
            LOG_ERROR_VISIBLE,
            LOG_CRITICAL_VISIBLE,
            ERROR_VISIBLE,
            INFO_VISIBLE,
        ):
            visible = self._visibility & flag != 0
            cur_visible = self._visibility_by_flags[flag]
            if cur_visible != visible:
                for widget in self._widgets_by_flag[flag]:
                    widget.setVisible(visible)
                self._visibility_by_flags[flag] = visible

    def set_log_filters(self, visibility_filter):
        if self._visibility == visibility_filter:
            return
        self._visibility = visibility_filter
        self._update_visibility()


class InstanceLogsWidget(QtWidgets.QWidget):
    """Widget showing logs of one publish instance.

    Args:
        instane (_InstanceItem): Item of instance used as data source.
        parent (QtWidgets.QWidget): Parent widget.
    """

    def __init__(self, instance, parent):
        super(InstanceLogsWidget, self).__init__(parent)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        label_widget = QtWidgets.QLabel(instance.label, self)
        label_widget.setObjectName("PublishInstanceLogsLabel")
        logs_grid = LogsGridView(instance.logs, self)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label_widget, 0)
        layout.addWidget(logs_grid, 0)

        self._logs_grid = logs_grid

    def set_log_filters(self, visibility_filter):
        """Change logs filter.

        Args:
            visibility_filter (int): Number contained of flags for each log
                type and level.
        """

        self._logs_grid.set_log_filters(visibility_filter)


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
                widget.set_log_filters(self._visible_filters)
                self._views_by_instance_id[instance_id] = widget
                self._content_layout.addWidget(widget, 0)
            else:
                widget.setVisible(True)

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
        self._clear_needed = True
        self._update_needed = True
        self._update_instances()

    def set_instances(self, instance_ids=None):
        """Set instance filter.

        Args:
            instance_ids (Optional[list[str]]): List of instances to keep
                visible. Pass empty list to hide all items.
        """

        self._instance_ids_filter = instance_ids
        self._update_needed = True
        self._update_instances()


class ReportsWidget(QtWidgets.QWidget):
    def __init__(self, controller, parent):
        super(ReportsWidget, self).__init__(parent)

        header_label = QtWidgets.QLabel(self)
        header_label.setAlignment(QtCore.Qt.AlignCenter)
        header_label.setObjectName("PublishInfoMainLabel")

        content_widget = QtWidgets.QWidget(self)

        views_widget = QtWidgets.QWidget(content_widget)

        instances_view = PublishInstancesViewWidget(content_widget)
        # TODO add validation errors view

        views_layout = QtWidgets.QHBoxLayout(views_widget)
        views_layout.setContentsMargins(0, 0, 0, 0)
        views_layout.addWidget(instances_view)

        details_widget = QtWidgets.QFrame(content_widget)
        details_widget.setObjectName("PublishInstancesDetails")

        logs_view = InstancesLogsView(details_widget)

        details_layout = QtWidgets.QHBoxLayout(details_widget)
        details_layout.addWidget(logs_view, 1)

        content_layout = QtWidgets.QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.addWidget(views_widget, 0)
        content_layout.addWidget(details_widget, 1)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(header_label, 0)
        layout.addWidget(content_widget, 1)

        instances_view.selection_changed.connect(self._on_selection_change)

        self._header_label = header_label
        self._instances_view = instances_view
        self._details_widget = details_widget

        self._logs_view = logs_view

        self._controller = controller

    def _update_label(self):
        if not self._controller.publish_has_started:
            # This probably never happen when this widget is visible
            header_label = "Publishing didn't start yet"
        elif self._controller.publish_has_crashed:
            header_label = "Publish error report"
        elif self._controller.publish_has_validation_errors:
            header_label = "Publish validation report"
        elif self._controller.publish_has_finished:
            header_label = "Publish success report"
        else:
            header_label = "Publish report"
        self._header_label.setText(header_label)

    def _get_instance_items(self):
        report = self._controller.get_publish_report()
        context_label = report["context"]["label"] or CONTEXT_LABEL
        instances_by_id = report["instances"]
        plugins_info = report["plugins_data"]
        logs_by_instance_id = collections.defaultdict(list)
        for plugin_info in plugins_info:
            for instance_info in plugin_info["instances_data"]:
                instance_id = instance_info["id"]
                logs_by_instance_id[instance_id].extend(
                    instance_info["logs"])

        context_item = _InstanceItem.create_context_item(
            context_label, logs_by_instance_id[None])
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
        self._update_label()
        if (
            not self._controller.publish_has_crashed
            and self._controller.publish_has_validation_errors
        ):
            pass
        else:
            instance_items = self._get_instance_items()
            self._instances_view.update_instances(instance_items)
            self._logs_view.update_instances(instance_items)

    def _on_selection_change(self):
        instance_ids = self._instances_view.get_selected_instance_ids()
        self._logs_view.set_instances(instance_ids)


class ReportPageWidget(QtWidgets.QFrame):
    """Widgets showing report for artis.

    There are 5 possible states:
    1. Publishing did not start yet.         > Only label.
    2. Publishing is paused.                ┐
    3. Publishing successfully finished.    │> Instances with logs.
    4. Publishing crashed.                  ┘
    5. Crashed because of validation error.  > Errors with logs.

    This widget is shown if validation error/s happened during validation part.

    Shows validation error titles with instances on which happened and
    validation error detail with possible actions (repair).

    ┌──────┬──────────────────┐
    │titles│  Details         │
    │      │                  │
    │      │                  │
    │      │                  │
    │      │                  │
    └──────┴──────────────────┘
    """

    def __init__(self, controller, parent):
        super(ReportPageWidget, self).__init__(parent)

        # Before publishing
        before_publish_widget = ValidationArtistMessage(
            "Nothing to report until you run publish", self
        )

        publish_instances_widget = ReportsWidget(controller, self)

        validations_widget = ValidationsWidget(controller, self)

        main_layout = QtWidgets.QStackedLayout(self)
        main_layout.addWidget(before_publish_widget)
        main_layout.addWidget(publish_instances_widget)
        main_layout.addWidget(validations_widget)

        main_layout.setCurrentWidget(before_publish_widget)

        controller.event_system.add_callback(
            "publish.process.started", self._on_publish_start
        )
        controller.event_system.add_callback(
            "publish.reset.finished", self._on_publish_reset
        )
        controller.event_system.add_callback(
            "publish.process.stopped", self._on_publish_stop
        )

        self._main_layout = main_layout

        self._before_publish_widget = before_publish_widget
        self._publish_instances_widget = publish_instances_widget
        self._validations_widget = validations_widget

        self._controller = controller

    def _set_current_widget(self, widget):
        self._main_layout.setCurrentWidget(widget)

    def _go_to_current_widget(self):
        if not self._controller.publish_has_started:
            new_widget = self._before_publish_widget
        elif (
            not self._controller.publish_has_crashed
            and self._controller.publish_has_validation_errors
        ):
            new_widget = self._validations_widget
            new_widget.update_data()
        else:
            new_widget = self._publish_instances_widget
            new_widget.update_data()

        self._set_current_widget(new_widget)
        self.updateGeometry()

    def _on_publish_start(self):
        self._go_to_current_widget()

    def _on_publish_reset(self):
        self._go_to_current_widget()

    def _on_publish_stop(self):
        self._go_to_current_widget()
