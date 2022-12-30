import collections
from openpype.client import get_projects, get_assets
from openpype.lib.events import EventSystem


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


class TaskItem:
    def __init__(self, asset_id, name, task_type, short_name):
        self.asset_id = asset_id
        self.name = name
        self.task_type = task_type
        self.short_name = short_name

    @classmethod
    def from_asset_doc(cls, asset_doc, project_doc):
        asset_tasks = asset_doc["data"].get("tasks") or {}
        project_task_types = project_doc["config"]["tasks"]
        output = []
        for task_name, task_info in asset_tasks.items():
            task_type = task_info.get("type")
            task_type_info = project_task_types.get(task_type) or {}
            output.append(cls(
                asset_doc["_id"],
                task_name,
                task_type,
                task_type_info.get("short_name")
            ))
        return output


class EntitiesModel:
    def __init__(self, event_system):
        self._event_system = event_system
        self._project_names = None
        self._project_docs_by_name = {}
        self._assets_by_project = {}
        self._tasks_by_asset_id = collections.defaultdict(dict)

    def has_cached_projects(self):
        return self._project_names is None

    def has_cached_assets(self, project_name):
        if not project_name:
            return True
        return project_name in self._assets_by_project

    def has_cached_tasks(self, project_name):
        return self.has_cached_assets(project_name)

    def get_projects(self):
        if self._project_names is None:
            self.refresh_projects()
        return list(self._project_names)

    def get_assets(self, project_name):
        if project_name not in self._assets_by_project:
            self.refresh_assets(project_name)
        return dict(self._assets_by_project[project_name])

    def get_tasks(self, project_name, asset_id):
        if not project_name or not asset_id:
            return []

        if project_name not in self._tasks_by_asset_id:
            self.refresh_assets(project_name)

        all_task_items = self._tasks_by_asset_id[project_name]
        asset_task_items = all_task_items.get(asset_id)
        return list(asset_task_items)

    def refresh_projects(self, force=False):
        self._event_system.emit(
            "projects.refresh.started", {}, "entities.model"
        )
        if force or self._project_names is None:
            project_names = []
            project_docs_by_name = {}
            for project_doc in get_projects():
                project_name = project_doc["name"]
                project_names.append(project_name)
                project_docs_by_name[project_name] = project_doc
            self._project_names = project_names
            self._project_docs_by_name = project_docs_by_name
        self._event_system.emit(
            "projects.refresh.finished", {}, "entities.model"
        )

    def _refresh_assets(self, project_name):
        asset_items_by_id = {}
        task_items_by_asset_id = {}
        self._assets_by_project[project_name] = asset_items_by_id
        self._tasks_by_asset_id[project_name] = task_items_by_asset_id
        if not project_name:
            return

        project_doc = self._project_docs_by_name[project_name]
        for asset_doc in get_assets(project_name):
            asset_item = AssetItem.from_doc(asset_doc)
            asset_items_by_id[asset_item.id] = asset_item
            task_items_by_asset_id[asset_item.id] = (
                TaskItem.from_asset_doc(asset_doc, project_doc)
            )

    def refresh_assets(self, project_name, force=False):
        self._event_system.emit(
            "assets.refresh.started",
            {"project_name": project_name},
            "entities.model"
        )

        if force or project_name not in self._assets_by_project:
            self._refresh_assets(project_name)

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
        self._event_system.emit(
            "project.changed",
            {"project_name": project_name},
            "selection.model"
        )

    def select_asset(self, asset_id):
        if self.asset_id == asset_id:
            return
        self.asset_id = asset_id
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

        event_system.add_callback("project.changed", self._on_project_change)

    @property
    def event_system(self):
        return self._event_system

    @property
    def model(self):
        return self._entities_model

    @property
    def selection_model(self):
        return self._selection_model

    def _on_project_change(self, event):
        project_name = event["project_name"]
        self.model.refresh_assets(project_name)

    def submit(self):
        project_name = self.selection_model.project_name
        asset_id = self.selection_model.asset_id
        task_name = self.selection_model.task_name
        self.dst_project_name = project_name
        self.dst_asset_id = asset_id
        self.dst_task_name = task_name
