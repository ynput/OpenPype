import collections

from qtpy import QtWidgets, QtGui, QtCore

from openpype.client import get_projects, get_assets
from openpype.lib.events import EventSystem


PROJECT_NAME_ROLE = QtCore.Qt.UserRole + 1
ASSET_NAME_ROLE = QtCore.Qt.UserRole + 2
ASSET_ICON_ROLE = QtCore.Qt.UserRole + 3
ASSET_ID_ROLE = QtCore.Qt.UserRole + 4


class AssetItem:
    def __init__(self, entity_id, name, icon, parent_id):
        self.id = entity_id
        self.name = name
        self.icon = icon
        self.parent_id = parent_id

    @classmethod
    def from_doc(cls, asset_doc):
        parent_id = asset_doc["data"].get("visualParent")
        if parent_id is not None:
            parent_id = str(parent_id)
        return cls(
            str(asset_doc["_id"]),
            asset_doc["name"],
            asset_doc["data"].get("icon"),
            parent_id
        )



class EntitiesModel:
    def __init__(self, event_system):
        self._event_system = event_system
        self._projects = None
        self._assets_by_project = {}
        self._tasks_by_asset_id = collections.defaultdict(dict)

    def has_cached_projects(self):
        return self._projects is None

    def has_cached_assets(self, project_name):
        if not project_name:
            return True
        return project_name in self._assets_by_project

    def has_cached_tasks(self, project_name):
        if not project_name:
            return True
        return project_name in self._assets_by_project

    def get_projects(self):
        if self._projects is not None:
            return list(self._projects)

        self.refresh_projects()

    def get_assets(self, project_name):
        if project_name in self._assets_by_project:
            return dict(self._assets_by_project[project_name])
        self.refresh_assets(project_name)
        return []

    def get_tasks(self, project_name, asset_id):
        output = []
        if not project_name or not asset_id:
            return output

        if project_name not in self._assets_by_project:
            self.refresh_assets(project_name)
            return output

        asset_docs = self._assets_by_project[project_name]
        asset_doc = asset_docs.get(asset_id)
        if not asset_doc:
            return output

        for task, _task_info in asset_doc["data"]["tasks"].items():
            output.append(task)
        return output

    def refresh_projects(self):
        self._projects = None
        self._event_system.emit(
            "projects.refresh.started", {}, "entities.model"
        )
        self._projects = [project["name"] for project in get_projects()]
        self._event_system.emit(
            "projects.refresh.finished", {}, "entities.model"
        )

    def refresh_assets(self, project_name):
        self._event_system.emit(
            "assets.refresh.started",
            {"project_name": project_name},
            "entities.model"
        )
        asset_docs = []
        if project_name:
            asset_docs = get_assets(project_name)
        asset_items_by_id = {}
        for asset_doc in asset_docs:
            asset_item = AssetItem.from_doc(asset_doc)
            asset_items_by_id[asset_item.id] = asset_item
        self._assets_by_project[project_name] = asset_items_by_id
        self._event_system.emit(
            "assets.refresh.finished",
            {"project_name": project_name},
            "entities.model"
        )


class SelectionModel:
    def __init__(self, event_system):
        self._event_system = event_system

        self.project_name = None
        self.asset_id = None
        self.task_name = None

    def select_project(self, project_name):
        if self.project_name == project_name:
            return

        self.project_name = project_name
        self.asset_id = None
        self.task_name = None
        self._event_system.emit(
            "project.changed",
            {"project_name": project_name},
            "selection.model"
        )

    def select_asset(self, asset_id):
        if self.asset_id == asset_id:
            return
        self.asset_id = asset_id
        self.task_name = None
        self._event_system.emit(
            "asset.changed",
            {
                "project_name": self.project_name,
                "asset_id": asset_id
            },
            "selection.model"
        )

    def select_task(self, task_name):
        if self.task_name == task_name:
            return
        self.task_name = task_name
        self._event_system.emit(
            "task.changed",
            {
                "project_name": self.project_name,
                "asset_id": self.asset_id,
                "task_name": task_name
            },
            "selection.model"
        )


class RepublisherDialogController:
    def __init__(self):
        event_system = EventSystem()
        entities_model = EntitiesModel(event_system)
        selection_model = SelectionModel(event_system)

        self._event_system = event_system
        self._entities_model = entities_model
        self._selection_model = selection_model

        self.dst_project_name = None
        self.dst_asset_id = None
        self.dst_task_name = None

    @property
    def event_system(self):
        return self._event_system

    @property
    def model(self):
        return self._entities_model

    @property
    def selection_model(self):
        return self._selection_model


class ProjectsModel(QtGui.QStandardItemModel):
    empty_text = "< Empty >"
    refreshing_text = "< Refreshing >"
    select_project_text = "< Select Project >"

    def __init__(self, controller):
        super().__init__()
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


class AssetsModel(QtGui.QStandardItemModel):
    empty_text = "< Empty >"

    def __init__(self, controller):
        super().__init__()
        self._controller = controller

        items = {}

        placeholder_item = QtGui.QStandardItem(self.empty_text)

        root_item = self.invisibleRootItem()
        root_item.appendRows([placeholder_item])
        items[None] = placeholder_item

        self.event_system.add_callback(
            "project.changed", self._on_project_change
        )
        self.event_system.add_callback(
            "assets.refresh.started", self._on_refresh_start
        )
        self.event_system.add_callback(
            "assets.refresh.finished", self._on_refresh_finish
        )

        self._items = {}

        self._placeholder_item = placeholder_item

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
        self._clear()

    def _on_refresh_start(self, event):
        pass

    def _on_refresh_finish(self, event):
        event_project_name = event["project_name"]
        project_name = self._controller.selection_model.project_name
        print("finished", event_project_name, project_name)
        if event_project_name != project_name:
            return

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
                    new_items.append(item)
                    self._items[asset_item.id] = item

                elif item.parent() is not parent_item:
                    new_items.append(item)

                item.setData(asset_item.name, QtCore.Qt.DisplayRole)
                item.setData(asset_item.id, ASSET_ID_ROLE)
                item.setData(asset_item.icon, ASSET_ICON_ROLE)

            if new_items:
                parent_item.appendRows(new_items)

        for item_id in items_to_remove:
            item = self._items.pop(item_id, None)
            if item is None:
                continue
            parent = item.parent()
            if parent is not None:
                parent.removeRow(item.row())


class RepublisherDialogWindow(QtWidgets.QWidget):
    def __init__(self, controller=None):
        super().__init__()
        if controller is None:
            controller = RepublisherDialogController()
        self._controller = controller

        left_widget = QtWidgets.QWidget(self)

        project_combobox = QtWidgets.QComboBox(left_widget)
        project_model = ProjectsModel(controller)
        project_delegate = QtWidgets.QStyledItemDelegate()
        project_combobox.setItemDelegate(project_delegate)
        project_combobox.setModel(project_model)

        asset_view = QtWidgets.QTreeView(self)
        asset_model = AssetsModel(controller)
        asset_view.setModel(asset_model)

        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.addWidget(project_combobox, 0)
        left_layout.addWidget(asset_view, 1)

        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.addWidget(left_widget)

        self._project_combobox = project_combobox
        self._project_model = project_model
        self._project_delegate = project_delegate

        self._asset_view = asset_view
        self._asset_model = asset_model

        self._first_show = True

    def showEvent(self, event):
        super().showEvent(event)
        if self._first_show:
            self._first_show = False
            self._controller.model.refresh_projects()


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