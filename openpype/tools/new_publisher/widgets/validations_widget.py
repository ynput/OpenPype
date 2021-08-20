from Qt import QtWidgets, QtCore


class ValidationErrorTitleWidget(QtWidgets.QFrame):
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

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self._mouse_pressed = True
        super(ValidationErrorTitleWidget, self).mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self._mouse_pressed:
            self._mouse_pressed = False
            if self.rect().contains(event.pos()):
                self.set_checked(True)

        super(ValidationErrorTitleWidget, self).mouseReleaseEvent(event)


class ValidationsWidget(QtWidgets.QWidget):
    def __init__(self, parent):
        super(ValidationsWidget, self).__init__(parent)

        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        errors_widget = QtWidgets.QWidget(self)
        errors_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        errors_layout = QtWidgets.QVBoxLayout(errors_widget)
        errors_layout.setContentsMargins(0, 0, 0, 0)

        error_details_widget = QtWidgets.QWidget(self)
        error_details_input = QtWidgets.QTextEdit(error_details_widget)
        error_details_input.setTextInteractionFlags(
            QtCore.Qt.TextBrowserInteraction
        )

        error_details_layout = QtWidgets.QVBoxLayout(error_details_widget)
        error_details_layout.addWidget(error_details_input)

        actions_widget = QtWidgets.QWidget(self)
        actions_widget.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        actions_layout = QtWidgets.QVBoxLayout(actions_widget)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(errors_widget, 0)
        layout.addWidget(error_details_widget, 1)
        layout.addWidget(actions_widget, 0)

        self._errors_widget = errors_widget
        self._errors_layout = errors_layout
        self._error_details_input = error_details_input
        self._actions_layout = actions_layout

        self._title_widgets = {}
        self._error_info = {}
        self._previous_checked = None

    def set_errors(self, errors):
        _old_title_widget = self._title_widgets
        self._title_widgets = {}
        self._error_info = {}
        self._previous_checked = None
        while self._errors_layout.count():
            item = self._errors_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        while self._actions_layout.count():
            self._actions_layout.takeAt(0)

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
