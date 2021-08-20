try:
    import commonmark
except Exception:
    commonmark = None

from Qt import QtWidgets, QtCore


class _ClickableFrame(QtWidgets.QFrame):
    def __init__(self, parent):
        super(_ClickableFrame, self).__init__(parent)

        self._mouse_pressed = False

    def _mouse_release_callback(self):
        pass

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._mouse_pressed = True
        super(_ClickableFrame, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._mouse_pressed:
            self._mouse_pressed = False
            if self.rect().contains(event.pos()):
                self._mouse_release_callback()

        super(_ClickableFrame, self).mouseReleaseEvent(event)


class ValidationErrorTitleFrame(_ClickableFrame):
    selected = QtCore.Signal(int)

    def __init__(self, index, error_info, parent):
        super(ValidationErrorTitleFrame, self).__init__(parent)

        self.setObjectName("ValidationErrorTitleFrame")

        exception = error_info["exception"]
        label_widget = QtWidgets.QLabel(exception.title, self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(label_widget)

        self._index = index
        self._error_info = error_info
        self._selected = False

        self._mouse_pressed = False

    @property
    def is_selected(self):
        return self._selected

    @property
    def index(self):
        return self._index

    def set_index(self, index):
        self._index = index

    def _change_style_property(self, selected):
        value = "1" if selected else ""
        self.setProperty("selected", value)
        self.style().polish(self)

    def set_selected(self, selected=None):
        if selected is None:
            selected = not self._selected

        elif selected == self._selected:
            return

        self._selected = selected
        self._change_style_property(selected)
        if selected:
            self.selected.emit(self._index)

    def _mouse_release_callback(self):
        self.set_selected(True)


class ActionButton(QtWidgets.QPushButton):
    action_clicked = QtCore.Signal(str)

    def __init__(self, action, parent):
        super(ActionButton, self).__init__(parent)

        action_label = action.label or action.__name__
        self.setText(action_label)

        # TODO handle icons
        # action.icon

        self.action = action
        self.clicked.connect(self._on_click)

    def _on_click(self):
        self.action_clicked.emit(self.action.id)


class ValidateActionsWidget(QtWidgets.QFrame):
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
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        self._actions_mapping = {}

    def set_plugin(self, plugin):
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


class ValidationsWidget(QtWidgets.QWidget):
    def __init__(self, controller, parent):
        super(ValidationsWidget, self).__init__(parent)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        errors_widget = QtWidgets.QWidget(self)
        errors_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        errors_widget.setFixedWidth(200)
        errors_layout = QtWidgets.QVBoxLayout(errors_widget)
        errors_layout.setContentsMargins(0, 0, 0, 0)

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

        content_layout.addWidget(errors_widget, 0)
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
        _old_title_widget = self._title_widgets
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
            widget = ValidationErrorTitleFrame(idx, item, self)
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
