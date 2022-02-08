# -*- coding: utf-8 -*-
try:
    import commonmark
except Exception:
    commonmark = None

from Qt import QtWidgets, QtCore, QtGui

from openpype.tools.utils import BaseClickableFrame
from .widgets import (
    IconValuePixmapLabel
)


class ValidationErrorInstanceList(QtWidgets.QListView):
    """List of publish instances that caused a validation error.

    Instances are collected per plugin's validation error title.
    """
    def __init__(self, *args, **kwargs):
        super(ValidationErrorInstanceList, self).__init__(*args, **kwargs)

        self.setObjectName("ValidationErrorInstanceList")

        self.setSelectionMode(QtWidgets.QListView.ExtendedSelection)

    def minimumSizeHint(self):
        result = super(ValidationErrorInstanceList, self).minimumSizeHint()
        result.setHeight(self.sizeHint().height())
        return result

    def sizeHint(self):
        row_count = self.model().rowCount()
        height = 0
        if row_count > 0:
            height = self.sizeHintForRow(0) * row_count
        return QtCore.QSize(self.width(), height)


class ValidationErrorTitleWidget(QtWidgets.QWidget):
    """Title of validation error.

    Widget is used as radio button so requires clickable functionality and
    changing style on selection/deselection.

    Has toggle button to show/hide instances on which validation error happened
    if there is a list (Valdation error may happen on context).
    """
    selected = QtCore.Signal(int)

    def __init__(self, index, error_info, parent):
        super(ValidationErrorTitleWidget, self).__init__(parent)

        self._index = index
        self._error_info = error_info
        self._selected = False

        title_frame = BaseClickableFrame(self)
        title_frame.setObjectName("ValidationErrorTitleFrame")
        title_frame._mouse_release_callback = self._mouse_release_callback

        toggle_instance_btn = QtWidgets.QToolButton(title_frame)
        toggle_instance_btn.setObjectName("ArrowBtn")
        toggle_instance_btn.setArrowType(QtCore.Qt.RightArrow)
        toggle_instance_btn.setMaximumWidth(14)

        exception = error_info["exception"]
        label_widget = QtWidgets.QLabel(exception.title, title_frame)

        title_frame_layout = QtWidgets.QHBoxLayout(title_frame)
        title_frame_layout.addWidget(toggle_instance_btn)
        title_frame_layout.addWidget(label_widget)

        instances_model = QtGui.QStandardItemModel()
        instances = error_info["instances"]
        context_validation = False
        if (
            not instances
            or (len(instances) == 1 and instances[0] is None)
        ):
            context_validation = True
            toggle_instance_btn.setArrowType(QtCore.Qt.NoArrow)
        else:
            items = []
            for instance in instances:
                label = instance.data.get("label") or instance.data.get("name")
                item = QtGui.QStandardItem(label)
                item.setFlags(
                    QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
                )
                item.setData(instance.id)
                items.append(item)

            instances_model.invisibleRootItem().appendRows(items)

        instances_view = ValidationErrorInstanceList(self)
        instances_view.setModel(instances_model)
        instances_view.setVisible(False)

        self.setLayoutDirection(QtCore.Qt.LeftToRight)

        view_layout = QtWidgets.QHBoxLayout()
        view_layout.setContentsMargins(0, 0, 0, 0)
        view_layout.setSpacing(0)
        view_layout.addSpacing(14)
        view_layout.addWidget(instances_view)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(title_frame)
        layout.addLayout(view_layout)

        if not context_validation:
            toggle_instance_btn.clicked.connect(self._on_toggle_btn_click)

        self._title_frame = title_frame

        self._toggle_instance_btn = toggle_instance_btn

        self._instances_model = instances_model
        self._instances_view = instances_view

    def _mouse_release_callback(self):
        """Mark this widget as selected on click."""
        self.set_selected(True)

    @property
    def is_selected(self):
        """Is widget marked a selected"""
        return self._selected

    @property
    def index(self):
        """Widget's index set by parent."""
        return self._index

    def set_index(self, index):
        """Set index of widget (called by parent)."""
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

        elif selected == self._selected:
            return

        self._selected = selected
        self._change_style_property(selected)
        if selected:
            self.selected.emit(self._index)

    def _on_toggle_btn_click(self):
        """Show/hide instances list."""
        new_visible = not self._instances_view.isVisible()
        self._instances_view.setVisible(new_visible)
        if new_visible:
            self._toggle_instance_btn.setArrowType(QtCore.Qt.DownArrow)
        else:
            self._toggle_instance_btn.setArrowType(QtCore.Qt.RightArrow)


class ActionButton(BaseClickableFrame):
    """Plugin's action callback button.

    Action may have label or icon or both.
    """
    action_clicked = QtCore.Signal(str)

    def __init__(self, action, parent):
        super(ActionButton, self).__init__(parent)

        self.setObjectName("ValidationActionButton")

        self.action = action

        action_label = action.label or action.__name__
        action_icon = getattr(action, "icon", None)
        label_widget = QtWidgets.QLabel(action_label, self)
        if action_icon:
            icon_label = IconValuePixmapLabel(action_icon, self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.addWidget(label_widget, 1)
        layout.addWidget(icon_label, 0)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum,
            self.sizePolicy().verticalPolicy()
        )

    def _mouse_release_callback(self):
        self.action_clicked.emit(self.action.id)


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

        self.controller = controller
        self._content_widget = content_widget
        self._content_layout = content_layout
        self._plugin = None
        self._actions_mapping = {}

    def clear(self):
        """Remove actions from widget."""
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._actions_mapping = {}

    def set_plugin(self, plugin):
        """Set selected plugin and show it's actions.

        Clears current actions from widget and recreate them from the plugin.
        """
        self.clear()
        self._plugin = plugin
        if not plugin:
            self.setVisible(False)
            return

        actions = getattr(plugin, "actions", [])
        for action in actions:
            if not action.active:
                continue

            if action.on not in ("failed", "all"):
                continue

            self._actions_mapping[action.id] = action

            action_btn = ActionButton(action, self._content_widget)
            action_btn.action_clicked.connect(self._on_action_click)
            self._content_layout.addWidget(action_btn)

        if self._content_layout.count() > 0:
            self.setVisible(True)
            self._content_layout.addStretch(1)
        else:
            self.setVisible(False)

    def _on_action_click(self, action_id):
        action = self._actions_mapping[action_id]
        self.controller.run_action(self._plugin, action)


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


class ValidationsWidget(QtWidgets.QWidget):
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
    ├──────┴────────────────┴───────┤
    │         Publish buttons       │
    └───────────────────────────────┘
    """
    def __init__(self, controller, parent):
        super(ValidationsWidget, self).__init__(parent)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        errors_scroll = VerticallScrollArea(self)
        errors_scroll.setWidgetResizable(True)

        errors_widget = QtWidgets.QWidget(errors_scroll)
        errors_widget.setFixedWidth(200)
        errors_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        errors_layout = QtWidgets.QVBoxLayout(errors_widget)
        errors_layout.setContentsMargins(0, 0, 0, 0)

        errors_scroll.setWidget(errors_widget)

        error_details_widget = QtWidgets.QWidget(self)
        error_details_input = QtWidgets.QTextEdit(error_details_widget)
        error_details_input.setObjectName("InfoText")
        error_details_input.setTextInteractionFlags(
            QtCore.Qt.TextBrowserInteraction
        )

        actions_widget = ValidateActionsWidget(controller, self)
        actions_widget.setFixedWidth(140)

        error_details_layout = QtWidgets.QHBoxLayout(error_details_widget)
        error_details_layout.addWidget(error_details_input, 1)
        error_details_layout.addWidget(actions_widget, 0)

        content_layout = QtWidgets.QHBoxLayout()
        content_layout.setSpacing(0)
        content_layout.setContentsMargins(0, 0, 0, 0)

        content_layout.addWidget(errors_scroll, 0)
        content_layout.addWidget(error_details_widget, 1)

        top_label = QtWidgets.QLabel("Publish validation report", self)
        top_label.setObjectName("PublishInfoMainLabel")
        top_label.setAlignment(QtCore.Qt.AlignCenter)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(top_label)
        layout.addLayout(content_layout)

        self._top_label = top_label
        self._errors_widget = errors_widget
        self._errors_layout = errors_layout
        self._error_details_widget = error_details_widget
        self._error_details_input = error_details_input
        self._actions_widget = actions_widget

        self._title_widgets = {}
        self._error_info = {}
        self._previous_select = None

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
        self._error_details_widget.setVisible(False)
        self._errors_widget.setVisible(False)
        self._actions_widget.setVisible(False)

    def set_errors(self, errors):
        """Set errors into context and created titles."""
        self.clear()
        if not errors:
            return

        self._top_label.setVisible(True)
        self._error_details_widget.setVisible(True)
        self._errors_widget.setVisible(True)

        errors_by_title = []
        for plugin_info in errors:
            titles = []
            exception_by_title = {}
            instances_by_title = {}

            for error_info in plugin_info["errors"]:
                exception = error_info["exception"]
                title = exception.title
                if title not in titles:
                    titles.append(title)
                    instances_by_title[title] = []
                    exception_by_title[title] = exception
                instances_by_title[title].append(error_info["instance"])

            for title in titles:
                errors_by_title.append({
                    "plugin": plugin_info["plugin"],
                    "exception": exception_by_title[title],
                    "instances": instances_by_title[title]
                })

        for idx, item in enumerate(errors_by_title):
            widget = ValidationErrorTitleWidget(idx, item, self)
            widget.selected.connect(self._on_select)
            self._errors_layout.addWidget(widget)
            self._title_widgets[idx] = widget
            self._error_info[idx] = item

        self._errors_layout.addStretch(1)

        if self._title_widgets:
            self._title_widgets[0].set_selected(True)

    def _on_select(self, index):
        if self._previous_select:
            if self._previous_select.index == index:
                return
            self._previous_select.set_selected(False)

        self._previous_select = self._title_widgets[index]

        error_item = self._error_info[index]

        dsc = error_item["exception"].description
        if commonmark:
            html = commonmark.commonmark(dsc)
            self._error_details_input.setHtml(html)
        else:
            self._error_details_input.setMarkdown(dsc)
        self._actions_widget.set_plugin(error_item["plugin"])
