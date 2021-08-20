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


class ValidationErrorTitleWidget(_ClickableFrame):
    checked = QtCore.Signal(int)

    def __init__(self, index, error_info, parent):
        super(ValidationErrorTitleWidget, self).__init__(parent)

        self.setObjectName("ValidationErrorTitleWidget")

        exception = error_info["exception"]
        label_widget = QtWidgets.QLabel(exception.title, self)

        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(label_widget)

        self._index = index
        self._error_info = error_info
        self._checked = False

        self._mouse_pressed = False

    @property
    def is_checked(self):
        return self._checked

    @property
    def index(self):
        return self._index

    def set_index(self, index):
        self._index = index

    def _change_style_property(self, checked):
        value = "1" if checked else ""
        self.setProperty("checked", value)
        self.style().polish(self)

    def set_checked(self, checked=None):
        if checked is None:
            checked = not self._checked

        elif checked == self._checked:
            return

        self._checked = checked
        self._change_style_property(checked)
        if checked:
            self.checked.emit(self._index)

    def _mouse_release_callback(self):
        self.set_checked(True)


class ActionWidget(_ClickableFrame):
    action_clicked = QtCore.Signal(str)

    def __init__(self, action, parent):
        super(ActionWidget, self).__init__(parent)

        self.setObjectName("PublishPluginActionWidget")

        self._action_id = action.id

        action_label = action.label or action.__name__
        # TODO handle icons
        # action.icon

        lable_widget = QtWidgets.QLabel(action_label, self)
        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(lable_widget)

    def _mouse_release_callback(self):
        self.action_clicked.emit(self._action_id)


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

            action_widget = ActionWidget(action, self._content_widget)
            action_widget.action_clicked.connect(self._on_action_click)
            self._content_layout.addWidget(action_widget)

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

        error_details_layout = QtWidgets.QVBoxLayout(error_details_widget)
        error_details_layout.addWidget(error_details_input)

        actions_widget = ValidateActionsWidget(controller, self)
        actions_widget.setFixedWidth(140)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(errors_widget, 0)
        layout.addWidget(error_details_widget, 1)
        layout.addWidget(actions_widget, 0)

        self._errors_widget = errors_widget
        self._errors_layout = errors_layout
        self._error_details_widget = error_details_widget
        self._error_details_input = error_details_input
        self._actions_widget = actions_widget

        self._title_widgets = {}
        self._error_info = {}
        self._previous_checked = None

    def clear(self):
        _old_title_widget = self._title_widgets
        self._title_widgets = {}
        self._error_info = {}
        self._previous_checked = None
        while self._errors_layout.count():
            item = self._errors_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self._error_details_widget.setVisible(False)
        self._errors_widget.setVisible(False)
        self._actions_widget.setVisible(False)

    def set_errors(self, errors):
        self.clear()
        if not errors:
            return

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
            widget.checked.connect(self._on_checked)
            self._errors_layout.addWidget(widget)
            self._title_widgets[idx] = widget
            self._error_info[idx] = item

        self._errors_layout.addStretch(1)

        if self._title_widgets:
            self._title_widgets[0].set_checked(True)

    def _on_checked(self, index):
        if self._previous_checked:
            if self._previous_checked.index == index:
                return
            self._previous_checked.set_checked(False)

        self._previous_checked = self._title_widgets[index]

        error_item = self._error_info[index]

        self._error_details_input.setMarkdown(
            error_item["exception"].description
        )
        self._actions_widget.set_plugin(error_item["plugin"])
