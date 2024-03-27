import re
import collections
import threading

from openpype.client import (
    get_projects,
    get_assets,
    get_asset_by_id,
    get_subset_by_id,
    get_version_by_id,
    get_representations,
)
from openpype.settings import get_project_settings
from openpype.lib import prepare_template_data
from openpype.lib.events import EventSystem
from openpype.pipeline.create import (
    SUBSET_NAME_ALLOWED_SYMBOLS,
    get_subset_name_template,
)

from .control_integrate import (
    ProjectPushItem,
    ProjectPushItemProcess,
    ProjectPushItemStatus,
)


class AssetItem:
    def __init__(
        self,
        entity_id,
        name,
        icon_name,
        icon_color,
        parent_id,
        has_children
    ):
        self.id = entity_id
        self.name = name
        self.icon_name = icon_name
        self.icon_color = icon_color
        self.parent_id = parent_id
        self.has_children = has_children

    @classmethod
    def from_doc(cls, asset_doc, has_children=True):
        parent_id = asset_doc["data"].get("visualParent")
        if parent_id is not None:
            parent_id = str(parent_id)
        return cls(
            str(asset_doc["_id"]),
            asset_doc["name"],
            asset_doc["data"].get("icon"),
            asset_doc["data"].get("color"),
            parent_id,
            has_children
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
    def __init__(self, event_system, library_filter=True):
        self._event_system = event_system
        self._project_names = None
        self._project_docs_by_name = {}
        self._assets_by_project = {}
        self._tasks_by_asset_id = collections.defaultdict(dict)
        self.library_filter = library_filter

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

    def get_asset_by_id(self, project_name, asset_id):
        return self._assets_by_project[project_name].get(asset_id)

    def get_tasks(self, project_name, asset_id):
        if not project_name or not asset_id:
            return []

        if project_name not in self._tasks_by_asset_id:
            self.refresh_assets(project_name)

        all_task_items = self._tasks_by_asset_id[project_name]
        asset_task_items = all_task_items.get(asset_id)
        if not asset_task_items:
            return []
        return list(asset_task_items)

    def refresh_projects(self, force=False):
        self._event_system.emit(
            "projects.refresh.started", {}, "entities.model"
        )
        if force or self._project_names is None:
            project_names = []
            project_docs_by_name = {}
            for project_doc in get_projects():
                library_project = project_doc["data"].get("library_project")
                if not library_project and self.library_filter:
                    continue
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
        asset_docs_by_parent_id = collections.defaultdict(list)
        for asset_doc in get_assets(project_name):
            parent_id = asset_doc["data"].get("visualParent")
            asset_docs_by_parent_id[parent_id].append(asset_doc)

        hierarchy_queue = collections.deque()
        for asset_doc in asset_docs_by_parent_id[None]:
            hierarchy_queue.append(asset_doc)

        while hierarchy_queue:
            asset_doc = hierarchy_queue.popleft()
            children = asset_docs_by_parent_id[asset_doc["_id"]]
            asset_item = AssetItem.from_doc(asset_doc, len(children) > 0)
            asset_items_by_id[asset_item.id] = asset_item
            task_items_by_asset_id[asset_item.id] = (
                TaskItem.from_asset_doc(asset_doc, project_doc)
            )
            for child in children:
                hierarchy_queue.append(child)

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


class UserPublishValues:
    """Helper object to validate values required for push to different project.

    Args:
        event_system (EventSystem): Event system to catch and emit events.
        new_asset_name (str): Name of new asset name.
        variant (str): Variant for new subset name in new project.
    """

    asset_name_regex = re.compile("^[a-zA-Z0-9_.]+$")
    variant_regex = re.compile("^[{}]+$".format(SUBSET_NAME_ALLOWED_SYMBOLS))

    def __init__(self, event_system):
        self._event_system = event_system
        self._new_asset_name = None
        self._variant = None
        self._comment = None
        self._is_variant_valid = False
        self._is_new_asset_name_valid = False

        self.set_new_asset("")
        self.set_variant("")
        self.set_comment("")

    @property
    def new_asset_name(self):
        return self._new_asset_name

    @property
    def variant(self):
        return self._variant

    @property
    def comment(self):
        return self._comment

    @property
    def is_variant_valid(self):
        return self._is_variant_valid

    @property
    def is_new_asset_name_valid(self):
        return self._is_new_asset_name_valid

    @property
    def is_valid(self):
        return self.is_variant_valid and self.is_new_asset_name_valid

    def set_variant(self, variant):
        if variant == self._variant:
            return

        old_variant = self._variant
        old_is_valid = self._is_variant_valid

        self._variant = variant
        is_valid = False
        if variant:
            is_valid = self.variant_regex.match(variant) is not None
        self._is_variant_valid = is_valid

        changes = {
            key: {"new": new, "old": old}
            for key, old, new in (
                ("variant", old_variant, variant),
                ("is_valid", old_is_valid, is_valid)
            )
        }

        self._event_system.emit(
            "variant.changed",
            {
                "variant": variant,
                "is_valid": self._is_variant_valid,
                "changes": changes
            },
            "user_values"
        )

    def set_new_asset(self, asset_name):
        if self._new_asset_name == asset_name:
            return
        old_asset_name = self._new_asset_name
        old_is_valid = self._is_new_asset_name_valid
        self._new_asset_name = asset_name
        is_valid = True
        if asset_name:
            is_valid = (
                self.asset_name_regex.match(asset_name) is not None
            )
        self._is_new_asset_name_valid = is_valid
        changes = {
            key: {"new": new, "old": old}
            for key, old, new in (
                ("new_asset_name", old_asset_name, asset_name),
                ("is_valid", old_is_valid, is_valid)
            )
        }

        self._event_system.emit(
            "new_asset_name.changed",
            {
                "new_asset_name": self._new_asset_name,
                "is_valid": self._is_new_asset_name_valid,
                "changes": changes
            },
            "user_values"
        )

    def set_comment(self, comment):
        if comment == self._comment:
            return
        old_comment = self._comment
        self._comment = comment
        self._event_system.emit(
            "comment.changed",
            {
                "comment": comment,
                "changes": {
                    "comment": {"new": comment, "old": old_comment}
                }
            },
            "user_values"
        )


class PushToContextController:
    def __init__(
        self, project_name=None, version_id=None, library_filter=True
    ):
        self._src_project_name = None
        self._src_version_id = None
        self._src_asset_doc = None
        self._src_subset_doc = None
        self._src_version_doc = None

        event_system = EventSystem()
        entities_model = EntitiesModel(
            event_system, library_filter=library_filter
        )
        selection_model = SelectionModel(event_system)
        user_values = UserPublishValues(event_system)

        self._event_system = event_system
        self._entities_model = entities_model
        self._selection_model = selection_model
        self._user_values = user_values

        event_system.add_callback("project.changed", self._on_project_change)
        event_system.add_callback("asset.changed", self._invalidate)
        event_system.add_callback("variant.changed", self._invalidate)
        event_system.add_callback("new_asset_name.changed", self._invalidate)

        self._submission_enabled = False
        self._process_thread = None
        self._process_item = None

        self.set_source(project_name, version_id)

    def _get_task_info_from_repre_docs(self, asset_doc, repre_docs):
        asset_tasks = asset_doc["data"].get("tasks") or {}
        found_comb = []
        for repre_doc in repre_docs:
            context = repre_doc["context"]
            task_info = context.get("task")
            if task_info is None:
                continue

            task_name = None
            task_type = None
            if isinstance(task_info, str):
                task_name = task_info
                asset_task_info = asset_tasks.get(task_info) or {}
                task_type = asset_task_info.get("type")

            elif isinstance(task_info, dict):
                task_name = task_info.get("name")
                task_type = task_info.get("type")

            if task_name and task_type:
                return task_name, task_type

            if task_name:
                found_comb.append((task_name, task_type))

        for task_name, task_type in found_comb:
            return task_name, task_type
        return None, None

    def _get_src_variant(self):
        project_name = self._src_project_name
        version_doc = self._src_version_doc
        asset_doc = self._src_asset_doc
        repre_docs = get_representations(
            project_name, version_ids=[version_doc["_id"]]
        )
        task_name, task_type = self._get_task_info_from_repre_docs(
            asset_doc, repre_docs
        )

        project_settings = get_project_settings(project_name)
        subset_doc = self.src_subset_doc
        family = subset_doc["data"].get("family")
        if not family:
            family = subset_doc["data"]["families"][0]
        template = get_subset_name_template(
            self._src_project_name,
            family,
            task_name,
            task_type,
            None,
            project_settings=project_settings
        )
        template_low = template.lower()
        variant_placeholder = "{variant}"
        if (
            variant_placeholder not in template_low
            or (not task_name and "{task" in template_low)
        ):
            return ""

        idx = template_low.index(variant_placeholder)
        template_s = template[:idx]
        template_e = template[idx + len(variant_placeholder):]
        fill_data = prepare_template_data({
            "family": family,
            "task": task_name
        })
        try:
            subset_s = template_s.format(**fill_data)
            subset_e = template_e.format(**fill_data)
        except Exception as exc:
            print("Failed format", exc)
            return ""

        subset_name = self.src_subset_doc["name"]
        if (
            (subset_s and not subset_name.startswith(subset_s))
            or (subset_e and not subset_name.endswith(subset_e))
        ):
            return ""

        if subset_s:
            subset_name = subset_name[len(subset_s):]
        if subset_e:
            subset_name = subset_name[:len(subset_e)]
        return subset_name

    def set_source(self, project_name, version_id):
        if (
            project_name == self._src_project_name
            and version_id == self._src_version_id
        ):
            return

        self._src_project_name = project_name
        self._src_version_id = version_id
        asset_doc = None
        subset_doc = None
        version_doc = None
        if project_name and version_id:
            version_doc = get_version_by_id(project_name, version_id)

        if version_doc:
            subset_doc = get_subset_by_id(project_name, version_doc["parent"])

        if subset_doc:
            asset_doc = get_asset_by_id(project_name, subset_doc["parent"])

        self._src_asset_doc = asset_doc
        self._src_subset_doc = subset_doc
        self._src_version_doc = version_doc
        if asset_doc:
            self.user_values.set_new_asset(asset_doc["name"])
            variant = self._get_src_variant()
            if variant:
                self.user_values.set_variant(variant)

            comment = version_doc["data"].get("comment")
            if comment:
                self.user_values.set_comment(comment)

        self._event_system.emit(
            "source.changed", {
                "project_name": project_name,
                "version_id": version_id
            },
            "controller"
        )

    @property
    def src_project_name(self):
        return self._src_project_name

    @property
    def src_version_id(self):
        return self._src_version_id

    @property
    def src_label(self):
        if not self._src_project_name or not self._src_version_id:
            return "Source is not defined"

        asset_doc = self.src_asset_doc
        if not asset_doc:
            return "Source is invalid"

        asset_path_parts = list(asset_doc["data"]["parents"])
        asset_path_parts.append(asset_doc["name"])
        asset_path = "/".join(asset_path_parts)
        subset_doc = self.src_subset_doc
        version_doc = self.src_version_doc
        return "Source: {}/{}/{}/v{:0>3}".format(
            self._src_project_name,
            asset_path,
            subset_doc["name"],
            version_doc["name"]
        )

    @property
    def src_version_doc(self):
        return self._src_version_doc

    @property
    def src_subset_doc(self):
        return self._src_subset_doc

    @property
    def src_asset_doc(self):
        return self._src_asset_doc

    @property
    def event_system(self):
        return self._event_system

    @property
    def model(self):
        return self._entities_model

    @property
    def selection_model(self):
        return self._selection_model

    @property
    def user_values(self):
        return self._user_values

    @property
    def submission_enabled(self):
        return self._submission_enabled

    def _on_project_change(self, event):
        project_name = event["project_name"]
        self.model.refresh_assets(project_name)
        self._invalidate()

    def _invalidate(self):
        submission_enabled = self._check_submit_validations()
        if submission_enabled == self._submission_enabled:
            return
        self._submission_enabled = submission_enabled
        self._event_system.emit(
            "submission.enabled.changed",
            {"enabled": submission_enabled},
            "controller"
        )

    def _check_submit_validations(self):
        if not self._user_values.is_valid:
            return False

        if not self.selection_model.project_name:
            return False

        if (
            not self._user_values.new_asset_name
            and not self.selection_model.asset_id
        ):
            return False

        return True

    def get_selected_asset_name(self):
        project_name = self._selection_model.project_name
        asset_id = self._selection_model.asset_id
        if not project_name or not asset_id:
            return None
        asset_item = self._entities_model.get_asset_by_id(
            project_name, asset_id
        )
        if asset_item:
            return asset_item.name
        return None

    def submit(self, wait=True, context_only=False):
        if not self.submission_enabled:
            return

        if self._process_thread is not None:
            return

        if context_only:
            return

        item = ProjectPushItem(
            self.src_project_name,
            self.src_version_id,
            self.selection_model.project_name,
            self.selection_model.asset_id,
            self.selection_model.task_name,
            self.user_values.variant,
            comment=self.user_values.comment,
            new_asset_name=self.user_values.new_asset_name,
            dst_version=1
        )

        status_item = ProjectPushItemStatus(event_system=self._event_system)
        process_item = ProjectPushItemProcess(item, status_item)
        self._process_item = process_item
        self._event_system.emit("submit.started", {}, "controller")
        if wait:
            self._submit_callback()
            self._process_item = None
            return process_item

        thread = threading.Thread(target=self._submit_callback)
        self._process_thread = thread
        thread.start()
        return process_item

    def wait_for_process_thread(self):
        if self._process_thread is None:
            return
        self._process_thread.join()
        self._process_thread = None

    def _submit_callback(self):
        process_item = self._process_item
        if process_item is None:
            return
        process_item.process()
        self._event_system.emit("submit.finished", {}, "controller")
        if process_item is self._process_item:
            self._process_item = None
