from Qt import QtCore, QtWidgets
import qtawesome
from .models import LogModel, LogsFilterProxy


class SearchComboBox(QtWidgets.QComboBox):
    """Searchable ComboBox with empty placeholder value as first value"""

    def __init__(self, parent=None, placeholder=""):
        super(SearchComboBox, self).__init__(parent)

        self.setEditable(True)
        self.setInsertPolicy(self.NoInsert)
        self.lineEdit().setPlaceholderText(placeholder)

        # Apply completer settings
        completer = self.completer()
        completer.setCompletionMode(completer.PopupCompletion)
        completer.setCaseSensitivity(QtCore.Qt.CaseInsensitive)

        # Force style sheet on popup menu
        # It won't take the parent stylesheet for some reason
        # todo: better fix for completer popup stylesheet
        if parent:
            popup = completer.popup()
            popup.setStyleSheet(parent.styleSheet())

        self.currentIndexChanged.connect(self.onIndexChange)

    def onIndexChange(self, index):
        print(index)

    def populate(self, items):
        self.clear()
        self.addItems([""])     # ensure first item is placeholder
        self.addItems(items)

    def get_valid_value(self):
        """Return the current text if it's a valid value else None

        Note: The empty placeholder value is valid and returns as ""

        """

        text = self.currentText()
        lookup = set(self.itemText(i) for i in range(self.count()))
        if text not in lookup:
            return None

        return text


class SelectableMenu(QtWidgets.QMenu):

    selection_changed = QtCore.Signal()

    def mouseReleaseEvent(self, event):
        action = self.activeAction()
        if action and action.isEnabled():
            action.trigger()
            self.selection_changed.emit()
        else:
            super(SelectableMenu, self).mouseReleaseEvent(event)


class CustomCombo(QtWidgets.QWidget):

    selection_changed = QtCore.Signal()

    def __init__(self, title, parent=None):
        super(CustomCombo, self).__init__(parent)
        toolbutton = QtWidgets.QToolButton(self)
        toolbutton.setText(title)

        toolmenu = SelectableMenu(self)

        toolbutton.setMenu(toolmenu)
        toolbutton.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(toolbutton)

        toolmenu.selection_changed.connect(self.selection_changed)

        self.toolbutton = toolbutton
        self.toolmenu = toolmenu
        self.main_layout = layout

    def populate(self, items):
        self.toolmenu.clear()
        self.addItems(items)

    def addItems(self, items):
        for item in items:
            action = self.toolmenu.addAction(item)
            action.setCheckable(True)
            action.setChecked(True)
            self.toolmenu.addAction(action)

    def items(self):
        for action in self.toolmenu.actions():
            yield action


class LogsWidget(QtWidgets.QWidget):
    """A widget that lists the published subsets for an asset"""

    def __init__(self, detail_widget, parent=None):
        super(LogsWidget, self).__init__(parent=parent)

        model = LogModel()
        proxy_model = LogsFilterProxy()
        proxy_model.setSourceModel(model)
        proxy_model.col_usernames = model.COLUMNS.index("username")

        filter_layout = QtWidgets.QHBoxLayout()

        user_filter = CustomCombo("Users", self)
        users = model.dbcon.distinct("username")
        user_filter.populate(users)
        user_filter.selection_changed.connect(self._user_changed)

        proxy_model.update_users_filter(users)

        level_filter = CustomCombo("Levels", self)
        levels = model.dbcon.distinct("level")
        level_filter.addItems(levels)
        level_filter.selection_changed.connect(self._level_changed)

        detail_widget.update_level_filter(levels)

        icon = qtawesome.icon("fa.refresh", color="white")
        refresh_btn = QtWidgets.QPushButton(icon, "")

        filter_layout.addWidget(user_filter)
        filter_layout.addWidget(level_filter)
        filter_layout.addStretch(1)
        filter_layout.addWidget(refresh_btn)

        view = QtWidgets.QTreeView(self)
        view.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(filter_layout)
        layout.addWidget(view)

        view.setModel(proxy_model)

        view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        view.setSortingEnabled(True)
        view.sortByColumn(
            model.COLUMNS.index("started"),
            QtCore.Qt.DescendingOrder
        )

        view.selectionModel().selectionChanged.connect(self._on_index_change)
        refresh_btn.clicked.connect(self._on_refresh_clicked)

        # Store to memory
        self.model = model
        self.proxy_model = proxy_model
        self.view = view

        self.user_filter = user_filter
        self.level_filter = level_filter

        self.detail_widget = detail_widget
        self.refresh_btn = refresh_btn

        # prepare
        self.refresh()

    def refresh(self):
        self.model.refresh()
        self.detail_widget.refresh()

    def _on_refresh_clicked(self):
        self.refresh()

    def _on_index_change(self, to_index, from_index):
        index = self._selected_log()
        if index:
            logs = index.data(self.model.ROLE_LOGS)
        else:
            logs = []
        self.detail_widget.set_detail(logs)

    def _user_changed(self):
        checked_values = set()
        for action in self.user_filter.items():
            if action.isChecked():
                checked_values.add(action.text())
        self.proxy_model.update_users_filter(checked_values)

    def _level_changed(self):
        checked_values = set()
        for action in self.level_filter.items():
            if action.isChecked():
                checked_values.add(action.text())
        self.detail_widget.update_level_filter(checked_values)

    def on_context_menu(self, point):
        # TODO will be any actions? it's ready
        return

        point_index = self.view.indexAt(point)
        if not point_index.isValid():
            return

        # Get selected subsets without groups
        selection = self.view.selectionModel()
        rows = selection.selectedRows(column=0)

    def _selected_log(self):
        selection = self.view.selectionModel()
        rows = selection.selectedRows(column=0)
        if len(rows) == 1:
            return rows[0]
        return None


class OutputWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(OutputWidget, self).__init__(parent=parent)
        layout = QtWidgets.QVBoxLayout(self)

        show_timecode_checkbox = QtWidgets.QCheckBox("Show timestamp", self)

        output_text = QtWidgets.QTextEdit(self)
        output_text.setReadOnly(True)
        # output_text.setLineWrapMode(QtWidgets.QTextEdit.FixedPixelWidth)

        layout.addWidget(show_timecode_checkbox)
        layout.addWidget(output_text)

        show_timecode_checkbox.stateChanged.connect(
            self.on_show_timecode_change
        )
        self.setLayout(layout)
        self.output_text = output_text
        self.show_timecode_checkbox = show_timecode_checkbox

        self.refresh()

    def refresh(self):
        self.set_detail()

    def show_timecode(self):
        return self.show_timecode_checkbox.isChecked()

    def on_show_timecode_change(self):
        self.set_detail(self.las_logs)

    def update_level_filter(self, levels):
        self.filter_levels = set()
        for level in levels or tuple():
            self.filter_levels.add(level.lower())

        self.set_detail(self.las_logs)

    def add_line(self, line):
        self.output_text.append(line)

    def set_detail(self, logs=None):
        self.las_logs = logs
        self.output_text.clear()
        if not logs:
            return

        show_timecode = self.show_timecode()
        for log in logs:
            level = log["level"].lower()
            if level not in self.filter_levels:
                continue

            line_f = "<font color=\"White\">{message}"
            if level == "debug":
                line_f = (
                    "<font color=\"Yellow\"> -"
                    " <font color=\"Lime\">{{  {loggerName}  }}: ["
                    " <font color=\"White\">{message}"
                    " <font color=\"Lime\">]"
                )
            elif level == "info":
                line_f = (
                    "<font color=\"Lime\">>>> ["
                    " <font color=\"White\">{message}"
                    " <font color=\"Lime\">]"
                )
            elif level == "warning":
                line_f = (
                    "<font color=\"Yellow\">*** WRN:"
                    " <font color=\"Lime\"> >>> {{ {loggerName} }}: ["
                    " <font color=\"White\">{message}"
                    " <font color=\"Lime\">]"
                )
            elif level == "error":
                line_f = (
                    "<font color=\"Red\">!!! ERR:"
                    " <font color=\"White\">{timestamp}"
                    " <font color=\"Lime\">>>> {{ {loggerName} }}: ["
                    " <font color=\"White\">{message}"
                    " <font color=\"Lime\">]"
                )

            exc = log.get("exception")
            if exc:
                log["message"] = exc["message"]

            line = line_f.format(**log)

            if show_timecode:
                timestamp = log["timestamp"]
                line = timestamp.strftime("%Y-%d-%m %H:%M:%S") + " " + line

            self.add_line(line)

            if not exc:
                continue
            for _line in exc["stackTrace"].split("\n"):
                self.add_line(_line)
