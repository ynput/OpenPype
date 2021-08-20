from Qt import QtWidgets, QtCore


class ValidationErrorInfo:
    def __init__(self, title, detail, actions):
        self.title = title
        self.detail = detail
        self.actions = actions

global_msg = """
## Publish plugins

### Validate Scene Settings

#### Skip Resolution Check for Tasks

Set regex pattern(s) to look for in a Task name to skip resolution check against values from DB.

#### Skip Timeline Check for Tasks

Set regex pattern(s) to look for in a Task name to skip `frameStart`, `frameEnd` check against values from DB.

### AfterEffects Submit to Deadline

* `Use Published scene` - Set to True (green) when Deadline should take published scene as a source instead of uploaded local one.
* `Priority` - priority of job on farm
* `Primary Pool` - here is list of pool fetched from server you can select from.
* `Secondary Pool`
* `Frames Per Task` - number of sequence division between individual tasks (chunks)
making one job on farm.
"""


class ValidationErrorTitleWidget(QtWidgets.QFrame):
    checked = QtCore.Signal(int)

    def __init__(self, index, error_info, parent):
        super(ValidationErrorTitleWidget, self).__init__(parent)

        self.setObjectName("ValidationErrorTitleWidget")

        label_widget = QtWidgets.QLabel(error_info.title, self)

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

        self.set_errors([
            {
                "title": "Test 1",
                "detail": global_msg,
                "actions": []
            },
            {
                "title": "Test 2",
                "detail": "Detaile message about error 2",
                "actions": []
            },
            {
                "title": "Test 3",
                "detail": "Detaile message about error 3",
                "actions": []
            }
        ])

    def set_errors(self, errors):
        _old_title_widget = self._title_widgets
        self._title_widgets = {}
        self._error_info = {}
        self._previous_checked = None
        while self._errors_layout.count():
            self._errors_layout.takeAt(0)

        while self._actions_layout.count():
            self._actions_layout.takeAt(0)

        for idx, error in enumerate(errors):
            item = ValidationErrorInfo(
                error["title"], error["detail"], error["actions"]
            )
            widget = ValidationErrorTitleWidget(idx, item, self)
            widget.checked.connect(self._on_checked)
            self._errors_layout.addWidget(widget)
            self._title_widgets[idx] = widget
            self._error_info[idx] = item

        if self._title_widgets:
            self._title_widgets[0].set_checked(True)

        self._errors_layout.addStretch(1)

    def _on_checked(self, index):
        if self._previous_checked:
            if self._previous_checked.index == index:
                return
            self._previous_checked.set_checked(False)

        self._previous_checked = self._title_widgets[index]
        error_item = self._error_info[index]
        self._error_details_input.setMarkdown(error_item.detail)
