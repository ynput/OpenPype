import collections

from qtpy import QtWidgets, QtGui, QtCore

from openpype.style import load_stylesheet

from .control import RepublisherDialogController

PROJECT_NAME_ROLE = QtCore.Qt.UserRole + 1
ASSET_NAME_ROLE = QtCore.Qt.UserRole + 2
ASSET_ICON_ROLE = QtCore.Qt.UserRole + 3
ASSET_ID_ROLE = QtCore.Qt.UserRole + 4
TASK_NAME_ROLE = QtCore.Qt.UserRole + 5
TASK_TYPE_ROLE = QtCore.Qt.UserRole + 6


class ProjectsModel(QtGui.QStandardItemModel):
    empty_text = "< Empty >"
    refreshing_text = "< Refreshing >"
    select_project_text = "< Select Project >"

    def __init__(self, controller):
        super(ProjectsModel, self).__init__()
        self._controller = controller

        self.event_system.add_callback(
            "projects.refresh.finished", self._on_refresh_finish
        )

        placeholder_item = QtGui.QStandardItem(self.empty_text)

        root_item = self.invisibleRootItem()
        root_item.appendRows([placeholder_item])
        items = {None: placeholder_item}

        self._placeholder_item = placeholder_item
        self._items = items

    @property
    def event_system(self):
        return self._controller.event_system

    def _on_refresh_finish(self):
        root_item = self.invisibleRootItem()
        project_names = self._controller.model.get_projects()

        if not project_names:
            placeholder_text = self.empty_text
        else:
            placeholder_text = self.select_project_text
        self._placeholder_item.setData(placeholder_text, QtCore.Qt.DisplayRole)

        new_items = []
        if None not in self._items:
            new_items.append(self._placeholder_item)

        current_project_names = set(self._items.keys())
        for project_name in current_project_names - set(project_names):
            if project_name is None:
                continue
            item = self._items.pop(project_name)
            root_item.removeRow(item.row())

        for project_name in project_names:
            if project_name in self._items:
                continue
            item = QtGui.QStandardItem(project_name)
            item.setData(project_name, PROJECT_NAME_ROLE)
            new_items.append(item)

        if new_items:
            root_item.appendRows(new_items)


class ProjectProxyModel(QtCore.QSortFilterProxyModel):
    def __init__(self):
        super(ProjectProxyModel, self).__init__()
        self._filter_empty_projects = False

    def set_filter_empty_project(self, filter_empty_projects):
        if filter_empty_projects == self._filter_empty_projects:
            return
        self._filter_empty_projects = filter_empty_projects
        self.invalidate()

    def filterAcceptsRow(self, row, parent):
        if not self._filter_empty_projects:
            return True
        model = self.sourceModel()
        source_index = model.index(row, self.filterKeyColumn(), parent)
        if model.data(source_index, PROJECT_NAME_ROLE) is None:
            return False
        return True


class AssetsModel(QtGui.QStandardItemModel):
    empty_text = "< Empty >"

    def __init__(self, controller):
        super(AssetsModel, self).__init__()
        self._controller = controller

        placeholder_item = QtGui.QStandardItem(self.empty_text)
        placeholder_item.setFlags(QtCore.Qt.ItemIsEnabled)

        root_item = self.invisibleRootItem()
        root_item.appendRows([placeholder_item])

        self.event_system.add_callback(
            "project.changed", self._on_project_change
        )
        self.event_system.add_callback(
            "assets.refresh.started", self._on_refresh_start
        )
        self.event_system.add_callback(
            "assets.refresh.finished", self._on_refresh_finish
        )

        self._items = {None: placeholder_item}

        self._placeholder_item = placeholder_item
        self._last_project = None

    @property
    def event_system(self):
        return self._controller.event_system

    def _clear(self):
        placeholder_in = False
        root_item = self.invisibleRootItem()
        for row in reversed(range(root_item.rowCount())):
            item = root_item.child(row)
            asset_id = item.data(ASSET_ID_ROLE)
            if asset_id is None:
                placeholder_in = True
                continue
            root_item.removeRow(item.row())

        for key in tuple(self._items.keys()):
            if key is not None:
                self._items.pop(key)

        if not placeholder_in:
            root_item.appendRows([self._placeholder_item])
        self._items[None] = self._placeholder_item

    def _on_project_change(self, event):
        project_name = event["project_name"]
        if project_name == self._last_project:
            return

        self._last_project = project_name
        self._clear()

    def _on_refresh_start(self, event):
        pass

    def _on_refresh_finish(self, event):
        event_project_name = event["project_name"]
        project_name = self._controller.selection_model.project_name
        if event_project_name != project_name:
            return

        self._last_project = event["project_name"]
        if project_name is None:
            if None not in self._items:
                self._clear()
            return

        asset_items_by_id = self._controller.model.get_assets(project_name)
        if not asset_items_by_id:
            self._clear()
            return

        assets_by_parent_id = collections.defaultdict(list)
        for asset_item in asset_items_by_id.values():
            assets_by_parent_id[asset_item.parent_id].append(asset_item)

        root_item = self.invisibleRootItem()
        if None in self._items:
            self._items.pop(None)
            root_item.takeRow(self._placeholder_item.row())

        items_to_remove = set(self._items) - set(asset_items_by_id.keys())
        hierarchy_queue = collections.deque()
        hierarchy_queue.append((None, root_item))
        while hierarchy_queue:
            parent_id, parent_item = hierarchy_queue.popleft()
            new_items = []
            for asset_item in assets_by_parent_id[parent_id]:
                item = self._items.get(asset_item.id)
                if item is None:
                    item = QtGui.QStandardItem()
                    item.setFlags(
                        QtCore.Qt.ItemIsSelectable
                        | QtCore.Qt.ItemIsEnabled
                    )
                    new_items.append(item)
                    self._items[asset_item.id] = item

                elif item.parent() is not parent_item:
                    new_items.append(item)

                item.setData(asset_item.name, QtCore.Qt.DisplayRole)
                item.setData(asset_item.id, ASSET_ID_ROLE)
                item.setData(asset_item.icon, ASSET_ICON_ROLE)

                hierarchy_queue.append((asset_item.id, item))

            if new_items:
                parent_item.appendRows(new_items)

        for item_id in items_to_remove:
            item = self._items.pop(item_id, None)
            if item is None:
                continue
            parent = item.parent()
            if parent is not None:
                parent.removeRow(item.row())


class TasksModel(QtGui.QStandardItemModel):
    empty_text = "< Empty >"

    def __init__(self, controller):
        super(TasksModel, self).__init__()
        self._controller = controller

        placeholder_item = QtGui.QStandardItem(self.empty_text)
        placeholder_item.setFlags(QtCore.Qt.ItemIsEnabled)

        root_item = self.invisibleRootItem()
        root_item.appendRows([placeholder_item])

        self.event_system.add_callback(
            "project.changed", self._on_project_change
        )
        self.event_system.add_callback(
            "assets.refresh.finished", self._on_asset_refresh_finish
        )
        self.event_system.add_callback(
            "asset.changed", self._on_asset_change
        )

        self._items = {None: placeholder_item}

        self._placeholder_item = placeholder_item
        self._last_project = None

    @property
    def event_system(self):
        return self._controller.event_system

    def _clear(self):
        placeholder_in = False
        root_item = self.invisibleRootItem()
        for row in reversed(range(root_item.rowCount())):
            item = root_item.child(row)
            task_name = item.data(TASK_NAME_ROLE)
            if task_name is None:
                placeholder_in = True
                continue
            root_item.removeRow(item.row())

        for key in tuple(self._items.keys()):
            if key is not None:
                self._items.pop(key)

        if not placeholder_in:
            root_item.appendRows([self._placeholder_item])
        self._items[None] = self._placeholder_item

    def _on_project_change(self, event):
        project_name = event["project_name"]
        if project_name == self._last_project:
            return

        self._last_project = project_name
        self._clear()

    def _on_asset_refresh_finish(self, event):
        self._refresh(event["project_name"])

    def _on_asset_change(self, event):
        self._refresh(event["project_name"])

    def _refresh(self, new_project_name):
        project_name = self._controller.selection_model.project_name
        if new_project_name != project_name:
            return

        self._last_project = project_name
        if project_name is None:
            if None not in self._items:
                self._clear()
            return

        asset_id = self._controller.selection_model.asset_id
        task_items = self._controller.model.get_tasks(
            project_name, asset_id
        )
        if not task_items:
            self._clear()
            return

        root_item = self.invisibleRootItem()
        if None in self._items:
            self._items.pop(None)
            root_item.takeRow(self._placeholder_item.row())

        new_items = []
        task_names = set()
        for task_item in task_items:
            task_name = task_item.name
            item = self._items.get(task_name)
            if item is None:
                item = QtGui.QStandardItem()
                item.setFlags(
                    QtCore.Qt.ItemIsSelectable
                    | QtCore.Qt.ItemIsEnabled
                )
                new_items.append(item)
                self._items[task_name] = item

            item.setData(task_name, QtCore.Qt.DisplayRole)
            item.setData(task_name, TASK_NAME_ROLE)
            item.setData(task_item.task_type, TASK_TYPE_ROLE)

        if new_items:
            root_item.appendRows(new_items)

        items_to_remove = set(self._items) - task_names
        for item_id in items_to_remove:
            item = self._items.pop(item_id, None)
            if item is None:
                continue
            parent = item.parent()
            if parent is not None:
                parent.removeRow(item.row())


class RepublisherDialogWindow(QtWidgets.QWidget):
    def __init__(self, controller=None):
        super(RepublisherDialogWindow, self).__init__()
        if controller is None:
            controller = RepublisherDialogController()
        self._controller = controller

        main_splitter = QtWidgets.QSplitter(self)

        left_widget = QtWidgets.QWidget(main_splitter)

        project_combobox = QtWidgets.QComboBox(left_widget)
        project_model = ProjectsModel(controller)
        project_proxy = ProjectProxyModel()
        project_proxy.setSourceModel(project_model)
        project_delegate = QtWidgets.QStyledItemDelegate()
        project_combobox.setItemDelegate(project_delegate)
        project_combobox.setModel(project_proxy)

        asset_view = QtWidgets.QTreeView(left_widget)
        asset_view.setHeaderHidden(True)
        asset_model = AssetsModel(controller)
        asset_view.setModel(asset_model)

        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(project_combobox, 0)
        left_layout.addWidget(asset_view, 1)

        right_widget = QtWidgets.QWidget(main_splitter)

        task_view = QtWidgets.QListView(right_widget)
        task_proxy = QtCore.QSortFilterProxyModel()
        task_model = TasksModel(controller)
        task_proxy.setSourceModel(task_model)
        task_view.setModel(task_proxy)

        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(task_view, 1)

        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)

        btns_widget = QtWidgets.QWidget(self)
        close_btn = QtWidgets.QPushButton("Close", btns_widget)
        select_btn = QtWidgets.QPushButton("Select", btns_widget)

        btns_layout = QtWidgets.QHBoxLayout(btns_widget)
        btns_layout.setContentsMargins(0, 0, 0, 0)
        btns_layout.addStretch(1)
        btns_layout.addWidget(close_btn, 0)
        btns_layout.addWidget(select_btn, 0)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.addWidget(main_splitter, 1)
        main_layout.addWidget(btns_widget, 0)

        project_combobox.currentIndexChanged.connect(self._on_project_change)
        asset_view.selectionModel().selectionChanged.connect(
            self._on_asset_change
        )
        task_view.selectionModel().selectionChanged.connect(
            self._on_task_change
        )
        select_btn.clicked.connect(self._on_select_click)
        close_btn.clicked.connect(self._on_close_click)

        self._project_combobox = project_combobox
        self._project_model = project_model
        self._project_proxy = project_proxy
        self._project_delegate = project_delegate

        self._asset_view = asset_view
        self._asset_model = asset_model

        self._task_view = task_view

        self._first_show = True

    def showEvent(self, event):
        super(RepublisherDialogWindow, self).showEvent(event)
        if self._first_show:
            self._first_show = False
            self._controller.model.refresh_projects()
            self.setStyleSheet(load_stylesheet())

    def _on_project_change(self):
        idx = self._project_combobox.currentIndex()
        if idx < 0:
            self._project_proxy.set_filter_empty_project(False)
            return

        project_name = self._project_combobox.itemData(idx, PROJECT_NAME_ROLE)
        self._project_proxy.set_filter_empty_project(project_name is not None)
        self._controller.selection_model.select_project(project_name)

    def _on_asset_change(self):
        indexes = self._asset_view.selectedIndexes()
        index = next(iter(indexes), None)
        asset_id = None
        if index is not None:
            model = self._asset_view.model()
            asset_id = model.data(index, ASSET_ID_ROLE)
        self._controller.selection_model.select_asset(asset_id)

    def _on_task_change(self):
        indexes = self._task_view.selectedIndexes()
        index = next(iter(indexes), None)
        task_name = None
        if index is not None:
            model = self._task_view.model()
            task_name = model.data(index, TASK_NAME_ROLE)
        self._controller.selection_model.select_task(task_name)

    def _on_close_click(self):
        self.close()

    def _on_select_click(self):
        self._controller.submit()


def main():
    app = QtWidgets.QApplication.instance()
    if not app:
        app = QtWidgets.QApplication([])

    # TODO find way how to get these
    project_name = None
    representation_id = None

    # Show window dialog
    window = RepublisherDialogWindow()
    window.show()

    app.exec_()


if __name__ == "__main__":
    main()