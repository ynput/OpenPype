# -*- coding: utf-8 -*-
try:
    import commonmark
except Exception:
    commonmark = None

from qtpy import QtWidgets, QtCore, QtGui

from openpype.tools.utils import BaseClickableFrame, ClickableFrame
from .widgets import (
    IconValuePixmapLabel
)
from ..constants import (
    INSTANCE_ID_ROLE
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

    ┌──────┬────────────────┬───────┐
    │titles│                │actions│
    │      │                │       │
    │      │  Error detail  │       │
    │      │                │       │
    │      │                │       │
    └──────┴────────────────┴───────┘
    """

    def __init__(self, controller, parent):
        super(ValidationsWidget, self).__init__(parent)

        # Before publishing
        before_publish_widget = ValidationArtistMessage(
            "Nothing to report until you run publish", self
        )
        # After success publishing
        publish_started_widget = ValidationArtistMessage(
            "So far so good", self
        )
        # After success publishing
        publish_stop_ok_widget = ValidationArtistMessage(
            "Publishing finished successfully", self
        )
        # After failed publishing (not with validation error)
        publish_stop_fail_widget = ValidationArtistMessage(
            "This is not your fault...", self
        )

        # Validation errors
        validations_widget = QtWidgets.QWidget(self)

        content_widget = QtWidgets.QWidget(validations_widget)

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

        validation_layout = QtWidgets.QVBoxLayout(validations_widget)
        validation_layout.setContentsMargins(0, 0, 0, 0)
        validation_layout.addWidget(top_label, 0)
        validation_layout.addWidget(content_widget, 1)

        main_layout = QtWidgets.QStackedLayout(self)
        main_layout.addWidget(before_publish_widget)
        main_layout.addWidget(publish_started_widget)
        main_layout.addWidget(publish_stop_ok_widget)
        main_layout.addWidget(publish_stop_fail_widget)
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
        self._publish_started_widget = publish_started_widget
        self._publish_stop_ok_widget = publish_stop_ok_widget
        self._publish_stop_fail_widget = publish_stop_fail_widget
        self._validations_widget = validations_widget

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

    def _set_current_widget(self, widget):
        self._main_layout.setCurrentWidget(widget)

    def _on_publish_start(self):
        self._set_current_widget(self._publish_started_widget)

    def _on_publish_reset(self):
        self._set_current_widget(self._before_publish_widget)

    def _on_publish_stop(self):
        if self._controller.publish_has_crashed:
            self._set_current_widget(self._publish_stop_fail_widget)
            return

        if self._controller.publish_has_validation_errors:
            validation_errors = self._controller.get_validation_errors()
            self._set_current_widget(self._validations_widget)
            self._set_errors(validation_errors)
            return

        if self._controller.publish_has_finished:
            self._set_current_widget(self._publish_stop_ok_widget)
            return

        self._set_current_widget(self._publish_started_widget)

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
