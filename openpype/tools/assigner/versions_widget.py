from Qt import QtWidgets, QtCore, QtGui

from openpype.tools.utils.delegates import PrettyTimeDelegate

UNIQUE_ID_ROLE = QtCore.Qt.UserRole + 1
ASSET_NAME_ROLE = QtCore.Qt.UserRole + 2
FAMILY_ROLE = QtCore.Qt.UserRole + 3
FAMILY_ICON_ROLE = QtCore.Qt.UserRole + 4
VERSION_ROLE = QtCore.Qt.UserRole + 5
VERSION_ID_ROLE = QtCore.Qt.UserRole + 6
VERSION_EDIT_ROLE = QtCore.Qt.UserRole + 7
TIME_ROLE = QtCore.Qt.UserRole + 8
AUTHOR_ROLE = QtCore.Qt.UserRole + 9
FRAMES_ROLE = QtCore.Qt.UserRole + 10
DURATION_ROLE = QtCore.Qt.UserRole + 11
HANDLES_ROLE = QtCore.Qt.UserRole + 12
STEP_ROLE = QtCore.Qt.UserRole + 13


class IconSubsetItemWidget(QtWidgets.QWidget):
    def __init__(self, subset_item, parent):
        super(IconSubsetItemWidget, self).__init__(parent)

        label = QtWidgets.QLabel(subset_item.subset_name, self)
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.addWidget(label, 0)

        self.setStyleSheet("background: #ff0000;")

        # TODO Versions label is not enought!!!
        # - each version can have different thumbnail and infomation to
        #       show
        # - version change cause more changes
        # sorted_versions = subset_item.get_sorted_versions()
        # version_labels = [
        #     (version_item.id, version_item.label)
        #     for version_item in sorted_versions
        # ]
        # version_items_by_id = {
        #     version_item.id: version_item
        #     for version_item in sorted_versions
        # }
        # version_id = item.data(VERSION_ID_ROLE)
        # if version_id and version_id in version_items_by_id:
        #     version_item = version_items_by_id[version_id]
        # else:
        #     version_item = sorted_versions[0]
        #     version_id = version_item.id
        #
        # item.setData(subset_item.subset_name, QtCore.Qt.DisplayRole)
        # item.setData(subset_item.asset_name, ASSET_NAME_ROLE)
        # item.setData(subset_item.family, FAMILY_ROLE)
        # item.setData(None, FAMILY_ICON_ROLE)
        # item.setData(version_item.label, VERSION_ROLE)
        # item.setData(version_id, VERSION_ID_ROLE)
        # item.setData(version_labels, VERSION_EDIT_ROLE)
        # self._set_item_version(item_id, version_id)


class IconViewWidget(QtWidgets.QWidget):
    def __init__(self, controller, parent):
        super(IconViewWidget, self).__init__(parent)

        self._size_hint = QtCore.QSize(100, 100)

        test_decrease_btn = QtWidgets.QPushButton("-", self)
        test_increase_btn = QtWidgets.QPushButton("+", self)
        top_layout = QtWidgets.QHBoxLayout()
        top_layout.addStretch(1)
        top_layout.addWidget(test_decrease_btn, 0)
        top_layout.addWidget(test_increase_btn, 0)

        content_widget = QtWidgets.QWidget(self)
        content_layout = QtWidgets.QVBoxLayout(content_widget)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addLayout(top_layout, 0)
        main_layout.addWidget(content_widget, 1)

        controller.event_system.add_callback(
            "versions.clear", self._on_versions_clear
        )
        controller.event_system.add_callback(
            "versions.refresh.finished", self._on_version_refresh_finish
        )

        test_decrease_btn.clicked.connect(self._on_decrease)
        test_increase_btn.clicked.connect(self._on_increase)

        self._controller = controller

        self._content_widget = content_widget
        self._content_layout = content_layout

        self._widgets = {}
        self._items = {}
        self._views = []

    def _on_decrease(self):
        new_size_hint = QtCore.QSize(self._size_hint)
        new_size_hint.setWidth(new_size_hint.width() - 20)
        new_size_hint.setHeight(new_size_hint.height() - 20)
        self.set_item_size_hint(new_size_hint)

    def _on_increase(self):
        new_size_hint = QtCore.QSize(self._size_hint)
        new_size_hint.setWidth(new_size_hint.width() + 20)
        new_size_hint.setHeight(new_size_hint.height() + 20)
        self.set_item_size_hint(new_size_hint)

    def set_item_size_hint(self, new_size_hint):
        if new_size_hint.width() < 20:
            new_size_hint.setWidth(20)
        if new_size_hint.height() < 20:
            new_size_hint.setHeight(20)

        if new_size_hint == self._size_hint:
            return

        self._size_hint = new_size_hint
        for item in self._items.values():
            item.setData(new_size_hint, QtCore.Qt.SizeHintRole)
        for view in self._views:
            view.setGridSize(new_size_hint)

    def _on_versions_clear(self):
        self._clear()

    def _clear(self):
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setVisible(False)
                widget.deleteLater()
        self._widgets = {}
        self._items = {}
        self._views = []

    def _on_version_refresh_finish(self):
        self._clear()

        view = QtWidgets.QListView(self._content_widget)
        view.setSpacing(5)

        view.setMouseTracking(True)
        view.setGridSize(self._size_hint)
        # view.setSelectionRectVisible(True)
        view.setSelectionMode(view.ExtendedSelection)
        view.setResizeMode(view.Adjust)
        view.setFlow(view.LeftToRight)
        view.setViewMode(view.IconMode)
        view.setWrapping(True)
        view.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        subset_items = (
            self._controller.get_current_containers_subset_items()
        )
        new_items = {}
        widgets = {}
        for subset_item in subset_items:
            item_id = subset_item.id
            item = QtGui.QStandardItem()
            item.setData(item_id, UNIQUE_ID_ROLE)
            item.setData(self._size_hint, QtCore.Qt.SizeHintRole)
            new_items[item_id] = item
            widgets[item_id] = IconSubsetItemWidget(subset_item, view)

        model = QtGui.QStandardItemModel()
        for item in new_items.values():
            model.appendRow(item)

        view.setModel(model)
        for row in range(model.rowCount()):
            index = model.index(row, 0)
            item_id = index.data(UNIQUE_ID_ROLE)
            widget = widgets[item_id]
            view.setIndexWidget(index, widget)

        self._widgets = widgets
        self._views = [view]
        self._items = new_items

        self._content_layout.addWidget(view)


class VersionsWidget(QtWidgets.QWidget):
    def __init__(self, controller, parent):
        super(VersionsWidget, self).__init__(parent)

        versions_model = VersionsModel(controller)
        proxy_model = QtCore.QSortFilterProxyModel()
        proxy_model.setSourceModel(versions_model)

        icon_versions_view = IconViewWidget(controller, self)

        list_versions_view = QtWidgets.QTreeView(self)
        list_versions_view.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection)
        list_versions_view.setSortingEnabled(True)
        list_versions_view.sortByColumn(1, QtCore.Qt.AscendingOrder)
        list_versions_view.setAlternatingRowColors(True)
        list_versions_view.setIndentation(20)
        list_versions_view.setModel(proxy_model)

        versions_delegate = ListVersionDelegate(list_versions_view)
        version_column = versions_model.column_labels.index("Version")
        list_versions_view.setItemDelegateForColumn(
            version_column, versions_delegate
        )

        time_delegate = PrettyTimeDelegate(list_versions_view)
        time_column = versions_model.column_labels.index("Time")
        list_versions_view.setItemDelegateForColumn(time_column, time_delegate)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(list_versions_view, 1)
        layout.addWidget(icon_versions_view, 1)

        selection_change_timer = QtCore.QTimer()
        selection_change_timer.setInterval(100)
        selection_change_timer.setSingleShot(True)

        selection_model = list_versions_view.selectionModel()
        selection_model.selectionChanged.connect(self._on_selection_change)
        selection_change_timer.timeout.connect(self._on_selection_timer)

        self._versions_model = versions_model
        self._proxy_model = proxy_model

        self._list_versions_view = list_versions_view
        self._versions_delegate = versions_delegate
        self._time_delegate = time_delegate

        self._icon_versions_view = icon_versions_view

        self._selection_change_timer = selection_change_timer

        self._controller = controller

    def _on_selection_change(self):
        self._selection_change_timer.start()

    def _on_selection_timer(self):
        selection_model = self._list_versions_view.selectionModel()
        selected_ids = {
            index.data(VERSION_ID_ROLE)
            for index in selection_model.selectedIndexes()
        }

        self._controller.event_system.emit(
            "version.selection.changed",
            {"version_ids": list(selected_ids)}
        )


class VersionsModel(QtGui.QStandardItemModel):
    column_labels = (
        "Subset",
        "Asset",
        "Family",
        "Version",
        "Time",
        "Author",
        "Frames",
        "Duration",
        "Handles",
        "Step"
    )

    def __init__(self, controller):
        super(VersionsModel, self).__init__()

        self.setColumnCount(len(self.column_labels))

        controller.event_system.add_callback(
            "versions.clear", self._on_versions_clear
        )
        # controller.event_system.add_callback(
        #     "versions.refresh.started", self._on_version_refresh_start
        # )
        controller.event_system.add_callback(
            "versions.refresh.finished", self._on_version_refresh_finish
        )

        self._controller = controller

        self._items_by_id = {}
        self._subset_items_by_id = {}

    def _on_versions_clear(self):
        self._versions_model.clear()

    def _on_version_refresh_finish(self):
        subset_items = (
            self._controller.get_current_containers_subset_items()
        )
        items_ids_to_remove = set(self._items_by_id.keys())
        new_items = []
        for subset_item in subset_items:
            item_id = subset_item.id
            if item_id in self._items_by_id:
                items_ids_to_remove.remove(item_id)
                item = self._items_by_id[item_id]
            else:
                item = QtGui.QStandardItem()
                item.setData(item_id, UNIQUE_ID_ROLE)
                self._items_by_id[item_id] = item
                self._subset_items_by_id[item_id] = subset_item
                new_items.append(item)

            # TODO Versions label is not enought!!!
            # - each version can have different thumbnail and infomation to
            #       show
            # - version change cause more changes
            sorted_versions = subset_item.get_sorted_versions()
            version_labels = [
                (version_item.id, version_item.label)
                for version_item in sorted_versions
            ]
            version_items_by_id = {
                version_item.id: version_item
                for version_item in sorted_versions
            }
            version_id = item.data(VERSION_ID_ROLE)
            if version_id and version_id in version_items_by_id:
                version_item = version_items_by_id[version_id]
            else:
                version_item = sorted_versions[0]
                version_id = version_item.id

            item.setData(subset_item.subset_name, QtCore.Qt.DisplayRole)
            item.setData(subset_item.asset_name, ASSET_NAME_ROLE)
            item.setData(subset_item.family, FAMILY_ROLE)
            item.setData(None, FAMILY_ICON_ROLE)
            item.setData(version_item.label, VERSION_ROLE)
            item.setData(version_id, VERSION_ID_ROLE)
            item.setData(version_labels, VERSION_EDIT_ROLE)
            self._set_item_version(item_id, version_id)

        items_to_remove = []
        for item_id in items_ids_to_remove:
            self._subset_items_by_id.pop(item_id)
            items_to_remove.append(self._items_by_id.pop(item_id))

        root_item = self.invisibleRootItem()
        for item in items_to_remove:
            root_item.removeRow(item.row())

        if new_items:
            root_item.appendRows(new_items)

    def _data_display_role(self, index, role):
        col = index.column()
        new_index = True
        if col == 0:
            new_index = False
        elif col == 1:
            role = ASSET_NAME_ROLE
        elif col == 2:
            role = FAMILY_ROLE
        elif col == 3:
            role = VERSION_ROLE
        elif col == 4:
            role = TIME_ROLE
        elif col == 5:
            role = AUTHOR_ROLE
        elif col == 6:
            role = FRAMES_ROLE
        elif col == 7:
            role = DURATION_ROLE
        elif col == 8:
            role = HANDLES_ROLE
        elif col == 9:
            role = STEP_ROLE

        if new_index:
            index = self.index(index.row(), 0, index.parent())
        return super(VersionsModel, self).data(index, role)

    def _data_edit_role(self, index, role):
        col = index.column()
        new_index = True
        if col == 0:
            new_index = False
        elif col == 3:
            role = VERSION_EDIT_ROLE

        if new_index:
            index = self.index(index.row(), 0, index.parent())
        return super(VersionsModel, self).data(index, role)

    def _data_icon_role(self, index, role):
        col = index.column()
        new_index = True
        if col == 0:
            new_index = False
        elif col == 2:
            role = FAMILY_ICON_ROLE

        if new_index:
            index = self.index(index.row(), 0, index.parent())
        return super(VersionsModel, self).data(index, role)

    def data(self, index, role):
        if role == QtCore.Qt.DisplayRole:
            return self._data_display_role(index, role)

        if role == QtCore.Qt.EditRole:
            return self._data_edit_role(index, role)

        if role == QtCore.Qt.DecorationRole:
            return self._data_icon_role(index, role)

        index = self.index(index.row(), 0, index.parent())

        return super(VersionsModel, self).data(index, role)

    def setData(self, index, value, role=None):
        if role is None:
            role = QtCore.Qt.EditRole

        index = self.index(index.row(), 0, index.parent())

        if role == VERSION_ID_ROLE:
            if index.data(VERSION_ID_ROLE) != value:
                item_id = index.data(UNIQUE_ID_ROLE)
                self._set_item_version(item_id, value)
        return super(VersionsModel, self).setData(index, value, role)

    def _set_item_version(self, item_id, version_id):
        subset_item = self._subset_items_by_id[item_id]
        version_item = subset_item.get_version_by_id(version_id)

        item = self._items_by_id[item_id]
        item.setData(version_item.label, VERSION_ROLE)
        item.setData(version_item.time, TIME_ROLE)
        item.setData(version_item.author, AUTHOR_ROLE)
        item.setData(version_item.duration, DURATION_ROLE)
        item.setData(version_item.handles, HANDLES_ROLE)
        item.setData(version_item.step, STEP_ROLE)

    def flags(self, index):
        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        if index.column() == 3:
            flags |= QtCore.Qt.ItemIsEditable
        return flags

    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            return self.column_labels[section]
        return super(VersionsModel, self).headerData(
            section, orientation, role
        )


class ListVersionDelegate(QtWidgets.QStyledItemDelegate):
    """A delegate that display version integer formatted as version string."""

    version_changed = QtCore.Signal()

    def displayText(self, value, locale):
        if value:
            return str(value)
        return ""

    def paint(self, painter, option, index):
        fg_color = index.data(QtCore.Qt.ForegroundRole)
        if fg_color:
            if isinstance(fg_color, QtGui.QBrush):
                fg_color = fg_color.color()

            if not isinstance(fg_color, QtGui.QColor):
                fg_color = None

        if not fg_color:
            return super(ListVersionDelegate, self).paint(painter, option, index)

        if option.widget:
            style = option.widget.style()
        else:
            style = QtWidgets.QApplication.style()

        style.drawControl(
            style.CE_ItemViewItem, option, painter, option.widget
        )

        painter.save()

        text = self.displayText(
            index.data(QtCore.Qt.DisplayRole), option.locale
        )
        pen = painter.pen()
        pen.setColor(fg_color)
        painter.setPen(pen)

        text_rect = style.subElementRect(style.SE_ItemViewItemText, option)
        text_margin = style.proxy().pixelMetric(
            style.PM_FocusFrameHMargin, option, option.widget
        ) + 1

        painter.drawText(
            text_rect.adjusted(text_margin, 0, - text_margin, 0),
            option.displayAlignment,
            text
        )

        painter.restore()

    def createEditor(self, parent, option, index):
        editor = QtWidgets.QComboBox(parent)

        def commit_data():
            self.commitData.emit(editor)

        editor.currentIndexChanged.connect(commit_data)

        return editor

    def setEditorData(self, editor, index):
        value = index.data(VERSION_EDIT_ROLE)
        current_value = index.data(VERSION_ID_ROLE)
        current_item = None

        editor_model = editor.model()
        items = []
        for version_id, label in value:
            item = QtGui.QStandardItem(label)
            item.setData(version_id, VERSION_ID_ROLE)
            items.append(item)

            if current_item is None and version_id == current_value:
                current_item = item

        editor.clear()

        root_item = editor_model.invisibleRootItem()
        if items:
            root_item.appendRows(items)

        index = 0
        if current_item:
            index = current_item.row()

        editor.setCurrentIndex(index)

    def setModelData(self, editor, model, index):
        """Apply the integer version back in the model"""

        editor_model = editor.model()
        editor_index = editor_model.index(editor.currentIndex(), 0)
        version_id = editor_index.data(VERSION_ID_ROLE)
        model.setData(index, version_id, VERSION_ID_ROLE)
