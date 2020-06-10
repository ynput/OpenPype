from Qt import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import QVariant
from .models import LogModel


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


class CheckableComboBox2(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(CheckableComboBox, self).__init__(parent)
        self.view().pressed.connect(self.handleItemPressed)
        self._changed = False

    def handleItemPressed(self, index):
        item = self.model().itemFromIndex(index)
        if item.checkState() == QtCore.Qt.Checked:
            item.setCheckState(QtCore.Qt.Unchecked)
        else:
            item.setCheckState(QtCore.Qt.Checked)
        self._changed = True

    def hidePopup(self):
        if not self._changed:
            super(CheckableComboBox, self).hidePopup()
        self._changed = False

    def itemChecked(self, index):
        item = self.model().item(index, self.modelColumn())
        return item.checkState() == QtCore.Qt.Checked

    def setItemChecked(self, index, checked=True):
        item = self.model().item(index, self.modelColumn())
        if checked:
            item.setCheckState(QtCore.Qt.Checked)
        else:
            item.setCheckState(QtCore.Qt.Unchecked)


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

        layout = QtWidgets.QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(toolbutton)

        self.setLayout(layout)

        # toolmenu.selection_changed.connect(self.on_selection_changed)
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


class CheckableComboBox(QtWidgets.QComboBox):
    def __init__(self, parent=None):
        super(CheckableComboBox, self).__init__(parent)

        view = QtWidgets.QTreeView()
        view.header().hide()
        view.setRootIsDecorated(False)

        model = QtGui.QStandardItemModel()

        view.pressed.connect(self.handleItemPressed)
        self._changed = False

        self.setView(view)
        self.setModel(model)

        self.view = view
        self.model = model

    def handleItemPressed(self, index):
        item = self.model.itemFromIndex(index)
        if item.checkState() == QtCore.Qt.Checked:
            item.setCheckState(QtCore.Qt.Unchecked)
        else:
            item.setCheckState(QtCore.Qt.Checked)
        self._changed = True

    def hidePopup(self):
        if not self._changed:
            super(CheckableComboBox, self).hidePopup()
        self._changed = False

    def itemChecked(self, index):
        item = self.model.item(index, self.modelColumn())
        return item.checkState() == QtCore.Qt.Checked

    def setItemChecked(self, index, checked=True):
        item = self.model.item(index, self.modelColumn())
        if checked:
            item.setCheckState(QtCore.Qt.Checked)
        else:
            item.setCheckState(QtCore.Qt.Unchecked)

    def addItems(self, items):
        for text, checked in items:
            text_item = QtGui.QStandardItem(text)
            checked_item = QtGui.QStandardItem()
            checked_item.setData(QVariant(checked), QtCore.Qt.CheckStateRole)
            self.model.appendRow([text_item, checked_item])


class LogsWidget(QtWidgets.QWidget):
    """A widget that lists the published subsets for an asset"""

    active_changed = QtCore.Signal()

    def __init__(self, parent=None):
        super(LogsWidget, self).__init__(parent=parent)

        model = LogModel()

        filter_layout = QtWidgets.QHBoxLayout()

        # user_filter = SearchComboBox(self, "Users")
        user_filter = CustomCombo("Users", self)
        users = model.dbcon.distinct("user")
        user_filter.populate(users)
        user_filter.selection_changed.connect(self.user_changed)

        level_filter = CustomCombo("Levels", self)
        # levels = [(level, True) for level in model.dbcon.distinct("level")]
        levels = model.dbcon.distinct("level")
        level_filter.addItems(levels)

        date_from_label = QtWidgets.QLabel("From:")
        date_filter_from = QtWidgets.QDateTimeEdit()

        date_from_layout = QtWidgets.QVBoxLayout()
        date_from_layout.addWidget(date_from_label)
        date_from_layout.addWidget(date_filter_from)

        # now = datetime.datetime.now()
        # QtCore.QDateTime(
        #     now.year,
        #     now.month,
        #     now.day,
        #     now.hour,
        #     now.minute,
        #     second=0,
        #     msec=0,
        #     timeSpec=0
        # )
        date_to_label = QtWidgets.QLabel("To:")
        date_filter_to = QtWidgets.QDateTimeEdit()

        date_to_layout = QtWidgets.QVBoxLayout()
        date_to_layout.addWidget(date_to_label)
        date_to_layout.addWidget(date_filter_to)

        filter_layout.addWidget(user_filter)
        filter_layout.addWidget(level_filter)

        filter_layout.addLayout(date_from_layout)
        filter_layout.addLayout(date_to_layout)

        view = QtWidgets.QTreeView(self)
        view.setAllColumnsShowFocus(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(filter_layout)
        layout.addWidget(view)

        view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        view.setSortingEnabled(True)
        view.sortByColumn(
            model.COLUMNS.index("started"),
            QtCore.Qt.AscendingOrder
        )

        view.setModel(model)
        view.pressed.connect(self._on_activated)
        # prepare
        model.refresh()

        # Store to memory
        self.model = model
        self.view = view

        self.user_filter = user_filter
        self.level_filter = level_filter

    def _on_activated(self, *args, **kwargs):
        self.active_changed.emit()

    def user_changed(self):
        for action in self.user_filter.items():
            print(action)

    def on_context_menu(self, point):
        # TODO will be any actions? it's ready
        return

        point_index = self.view.indexAt(point)
        if not point_index.isValid():
            return

        # Get selected subsets without groups
        selection = self.view.selectionModel()
        rows = selection.selectedRows(column=0)

    def selected_log(self):
        selection = self.view.selectionModel()
        rows = selection.selectedRows(column=0)
        if len(rows) == 1:
            return rows[0]
        return None


class OutputWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(OutputWidget, self).__init__(parent=parent)
        layout = QtWidgets.QVBoxLayout(self)
        output_text = QtWidgets.QTextEdit()
        output_text.setReadOnly(True)
        # output_text.setLineWrapMode(QtWidgets.QTextEdit.FixedPixelWidth)

        layout.addWidget(output_text)

        self.setLayout(layout)
        self.output_text = output_text

    def add_line(self, line):
        self.output_text.append(line)

    def set_detail(self, node):
        self.output_text.clear()
        for log in node["_logs"]:
            level = log["level"].lower()

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

            self.add_line(line)

            if not exc:
                continue
            for _line in exc["stackTrace"].split("\n"):
                self.add_line(_line)


class LogDetailWidget(QtWidgets.QWidget):
    """A Widget that display information about a specific version"""
    data_rows = [
        "user",
        "message",
        "level",
        "logname",
        "method",
        "module",
        "fileName",
        "lineNumber",
        "host",
        "timestamp"
    ]

    html_text = u"""
<h3>{user} - {timestamp}</h3>
<b>User</b><br>{user}<br>
<br><b>Level</b><br>{level}<br>
<br><b>Message</b><br>{message}<br>
<br><b>Log Name</b><br>{logname}<br><br><b>Method</b><br>{method}<br>
<br><b>File</b><br>{fileName}<br>
<br><b>Line</b><br>{lineNumber}<br>
<br><b>Host</b><br>{host}<br>
<br><b>Timestamp</b><br>{timestamp}<br>
"""

    def __init__(self, parent=None):
        super(LogDetailWidget, self).__init__(parent=parent)

        layout = QtWidgets.QVBoxLayout(self)

        label = QtWidgets.QLabel("Detail")
        detail_widget = QtWidgets.QTextEdit()
        detail_widget.setReadOnly(True)
        layout.addWidget(label)
        layout.addWidget(detail_widget)

        self.detail_widget = detail_widget

        self.setEnabled(True)

        self.set_detail(None)

    def set_detail(self, detail_data):
        if not detail_data:
            self.detail_widget.setText("")
            return

        data = dict()
        for row in self.data_rows:
            value = detail_data.get(row) or "< Not set >"
            data[row] = value

        self.detail_widget.setHtml(self.html_text.format(**data))
