import getpass
from Qt import QtCore, QtWidgets, QtGui
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
    checked_changed = QtCore.Signal(bool)

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

    def select_items(self, items, ignore_input=False):
        if not isinstance(items, list):
            items = [items]

        for action in self.toolmenu.actions():
            check = True
            if (
                action.text() in items and ignore_input or
                action.text() not in items and not ignore_input
            ):
                check = False

            action.setChecked(check)

    def addItems(self, items):
        for item in items:
            action = self.toolmenu.addAction(item)
            action.setCheckable(True)
            self.toolmenu.addAction(action)
            action.setChecked(True)
            action.triggered.connect(self.checked_changed)

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
            checked_item.setData(
                QtCore.QVariant(checked), QtCore.Qt.CheckStateRole
            )
            self.model.appendRow([text_item, checked_item])


class FilterLogModel(QtCore.QSortFilterProxyModel):
    sub_dict = ["$gt", "$lt", "$not"]
    def __init__(self, key_values, parent=None):
        super(FilterLogModel, self).__init__(parent)
        self.allowed_key_values = key_values

    def filterAcceptsRow(self, row, parent):
        """
        Reimplemented from base class.
        """
        model = self.sourceModel()
        for key, values in self.allowed_key_values.items():
            col_indx = model.COLUMNS.index(key)
            value = model.index(row, col_indx, parent).data(
                QtCore.Qt.DisplayRole
            )
            if value not in values:
                return False
        return True


class LogsWidget(QtWidgets.QWidget):
    """A widget that lists the published subsets for an asset"""

    active_changed = QtCore.Signal()

    _level_order = [
        "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
    ]

    def __init__(self, parent=None):
        super(LogsWidget, self).__init__(parent=parent)

        model = LogModel()

        filter_layout = QtWidgets.QHBoxLayout()

        user_filter = CustomCombo("Users", self)
        users = model.dbcon.distinct("user")
        user_filter.populate(users)
        user_filter.checked_changed.connect(self.user_changed)
        user_filter.select_items(getpass.getuser())

        level_filter = CustomCombo("Levels", self)
        levels = model.dbcon.distinct("level")
        _levels = []
        for level in self._level_order:
            if level in levels:
                _levels.append(level)
        level_filter.populate(_levels)
        level_filter.checked_changed.connect(self.level_changed)

        # date_from_label = QtWidgets.QLabel("From:")
        # date_filter_from = QtWidgets.QDateTimeEdit()
        #
        # date_from_layout = QtWidgets.QVBoxLayout()
        # date_from_layout.addWidget(date_from_label)
        # date_from_layout.addWidget(date_filter_from)
        #
        # date_to_label = QtWidgets.QLabel("To:")
        # date_filter_to = QtWidgets.QDateTimeEdit()
        #
        # date_to_layout = QtWidgets.QVBoxLayout()
        # date_to_layout.addWidget(date_to_label)
        # date_to_layout.addWidget(date_filter_to)

        filter_layout.addWidget(user_filter)
        filter_layout.addWidget(level_filter)
        filter_layout.setAlignment(QtCore.Qt.AlignLeft)

        # filter_layout.addLayout(date_from_layout)
        # filter_layout.addLayout(date_to_layout)

        view = QtWidgets.QTreeView(self)
        view.setAllColumnsShowFocus(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(filter_layout)
        layout.addWidget(view)

        view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        view.setSortingEnabled(True)
        view.sortByColumn(
            model.COLUMNS.index("timestamp"),
            QtCore.Qt.AscendingOrder
        )

        key_val = {
            "user": users,
            "level": levels
        }
        proxy_model = FilterLogModel(key_val, view)
        proxy_model.setSourceModel(model)
        view.setModel(proxy_model)

        view.customContextMenuRequested.connect(self.on_context_menu)
        view.selectionModel().selectionChanged.connect(self.active_changed)

        # WARNING this is cool but slows down widget a lot
        # header = view.header()
        # # Enforce the columns to fit the data (purely cosmetic)
        # if Qt.__binding__ in ("PySide2", "PyQt5"):
        #     header.setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        # else:
        #     header.setResizeMode(QtWidgets.QHeaderView.ResizeToContents)

        # prepare
        model.refresh()

        # Store to memory
        self.model = model
        self.proxy_model = proxy_model
        self.view = view

        self.user_filter = user_filter
        self.level_filter = level_filter

    def user_changed(self):
        valid_actions = []
        for action in self.user_filter.items():
            if action.isChecked():
                valid_actions.append(action.text())

        self.proxy_model.allowed_key_values["user"] = valid_actions
        self.proxy_model.invalidate()

    def level_changed(self):
        valid_actions = []
        for action in self.level_filter.items():
            if action.isChecked():
                valid_actions.append(action.text())

        self.proxy_model.allowed_key_values["level"] = valid_actions
        self.proxy_model.invalidate()


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
