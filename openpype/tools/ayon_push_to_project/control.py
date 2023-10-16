import threading

from openpype.client import (
    get_asset_by_id,
    get_subset_by_id,
    get_version_by_id,
    get_representations,
)
from openpype.settings import get_project_settings
from openpype.lib import prepare_template_data
from openpype.lib.events import QueuedEventSystem
from openpype.pipeline.create import get_subset_name_template
from openpype.tools.ayon_utils.models import ProjectsModel, HierarchyModel

from .models import (
    PushToProjectSelectionModel,
    UserPublishValuesModel,
    IntegrateModel,
)


class PushToContextController:
    def __init__(self, project_name=None, version_id=None):
        self._event_system = self._create_event_system()

        self._projects_model = ProjectsModel(self)
        self._hierarchy_model = HierarchyModel(self)
        self._integrate_model = IntegrateModel(self)

        self._selection_model = PushToProjectSelectionModel(self)
        self._user_values = UserPublishValuesModel(self)

        self._src_project_name = None
        self._src_version_id = None
        self._src_asset_doc = None
        self._src_subset_doc = None
        self._src_version_doc = None
        self._src_label = None

        self._submission_enabled = False
        self._process_thread = None
        self._process_item_id = None

        self.set_source(project_name, version_id)

    # Events system
    def emit_event(self, topic, data=None, source=None):
        """Use implemented event system to trigger event."""

        if data is None:
            data = {}
        self._event_system.emit(topic, data, source)

    def register_event_callback(self, topic, callback):
        self._event_system.add_callback(topic, callback)

    def set_source(self, project_name, version_id):
        """Set source project and version.

        Args:
            project_name (Union[str, None]): Source project name.
            version_id (Union[str, None]): Source version id.
        """

        if (
            project_name == self._src_project_name
            and version_id == self._src_version_id
        ):
            return

        self._src_project_name = project_name
        self._src_version_id = version_id
        self._src_label = None
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
            self._user_values.set_new_folder_name(asset_doc["name"])
            variant = self._get_src_variant()
            if variant:
                self._user_values.set_variant(variant)

            comment = version_doc["data"].get("comment")
            if comment:
                self._user_values.set_comment(comment)

        self._emit_event(
            "source.changed",
            {
                "project_name": project_name,
                "version_id": version_id
            }
        )

    def get_source_label(self):
        """Get source label.

        Returns:
            str: Label describing source project and version as path.
        """

        if self._src_label is None:
            self._src_label = self._prepare_source_label()
        return self._src_label

    def get_project_items(self, sender=None):
        return self._projects_model.get_project_items(sender)

    def get_folder_items(self, project_name, sender=None):
        return self._hierarchy_model.get_folder_items(project_name, sender)

    def get_task_items(self, project_name, folder_id, sender=None):
        return self._hierarchy_model.get_task_items(
            project_name, folder_id, sender
        )

    def get_user_values(self):
        return self._user_values.get_data()

    def set_user_value_folder_name(self, folder_name):
        self._user_values.set_new_folder_name(folder_name)
        self._invalidate()

    def set_user_value_variant(self, variant):
        self._user_values.set_variant(variant)
        self._invalidate()

    def set_user_value_comment(self, comment):
        self._user_values.set_comment(comment)
        self._invalidate()

    def set_selected_project(self, project_name):
        self._selection_model.set_selected_project(project_name)
        self._invalidate()

    def set_selected_folder(self, folder_id):
        self._selection_model.set_selected_folder(folder_id)
        self._invalidate()

    def set_selected_task(self, task_id, task_name):
        self._selection_model.set_selected_task(task_id, task_name)

    def get_process_item_status(self, item_id):
        return self._integrate_model.get_item_status(item_id)

    # Processing methods
    def submit(self, wait=True):
        if not self._submission_enabled:
            return

        if self._process_thread is not None:
            return

        item_id = self._integrate_model.create_process_item(
            self._src_project_name,
            self._src_version_id,
            self._selection_model.get_selected_project_name(),
            self._selection_model.get_selected_folder_id(),
            self._selection_model.get_selected_task_name(),
            self._user_values.variant,
            comment=self._user_values.comment,
            new_folder_name=self._user_values.new_folder_name,
            dst_version=1
        )

        self._process_item_id = item_id
        self._emit_event("submit.started")
        if wait:
            self._submit_callback()
            self._process_item_id = None
            return item_id

        thread = threading.Thread(target=self._submit_callback)
        self._process_thread = thread
        thread.start()
        return item_id

    def wait_for_process_thread(self):
        if self._process_thread is None:
            return
        self._process_thread.join()
        self._process_thread = None

    def _prepare_source_label(self):
        if not self._src_project_name or not self._src_version_id:
            return "Source is not defined"

        asset_doc = self._src_asset_doc
        if not asset_doc:
            return "Source is invalid"

        folder_path_parts = list(asset_doc["data"]["parents"])
        folder_path_parts.append(asset_doc["name"])
        folder_path = "/".join(folder_path_parts)
        subset_doc = self._src_subset_doc
        version_doc = self._src_version_doc
        return "Source: {}/{}/{}/v{:0>3}".format(
            self._src_project_name,
            folder_path,
            subset_doc["name"],
            version_doc["name"]
        )

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
        subset_doc = self._src_subset_doc
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

        subset_name = self._src_subset_doc["name"]
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

    def _check_submit_validations(self):
        if not self._user_values.is_valid:
            return False

        if not self._selection_model.get_selected_project_name():
            return False

        if (
            not self._user_values.new_folder_name
            and not self._selection_model.get_selected_folder_id()
        ):
            return False
        return True

    def _invalidate(self):
        submission_enabled = self._check_submit_validations()
        if submission_enabled == self._submission_enabled:
            return
        self._submission_enabled = submission_enabled
        self._emit_event(
            "submission.enabled.changed",
            {"enabled": submission_enabled}
        )

    def _submit_callback(self):
        process_item_id = self._process_item_id
        if process_item_id is None:
            return
        self._integrate_model.integrate_item(process_item_id)
        self._emit_event("submit.finished", {})
        if process_item_id == self._process_item_id:
            self._process_item_id = None

    def _emit_event(self, topic, data=None):
        if data is None:
            data = {}
        self.emit_event(topic, data, "controller")

    def _create_event_system(self):
        return QueuedEventSystem()
