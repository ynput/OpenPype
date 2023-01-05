import os
import re
import copy
import socket
import itertools

from openpype.client import (
    get_project,
    get_asset_by_id,
    get_subset_by_id,
    get_subset_by_name,
    get_version_by_id,
    get_last_version_by_subset_id,
    get_version_by_name,
    get_representations,
    get_representation_by_name,
)
from openpype.client.operations import (
    OperationsSession,
    new_subset_document,
    new_version_doc,
    prepare_version_update_data,
)
from openpype.lib import (
    StringTemplate,
    get_openpype_username,
    get_formatted_current_time,
)
from openpype.settings import get_project_settings
from openpype.pipeline import Anatomy
from openpype.pipeline.template_data import get_template_data
from openpype.pipeline.publish import get_publish_template_name
from openpype.pipeline.create import get_subset_name

UNKNOWN = object()


class RepublishError(Exception):
    pass


class ProjectPushItem:
    def __init__(
        self,
        src_project_name,
        src_version_id,
        dst_project_name,
        dst_asset_id,
        dst_task_name,
        dst_version=None
    ):
        self.src_project_name = src_project_name
        self.src_version_id = src_version_id
        self.dst_project_name = dst_project_name
        self.dst_asset_id = dst_asset_id
        self.dst_task_name = dst_task_name
        self.dst_version = dst_version
        self._id = "|".join([
            src_project_name,
            src_version_id,
            dst_project_name,
            dst_asset_id,
            dst_task_name
        ])

    @property
    def id(self):
        return self._id

    def __repr__(self):
        return "{} - {} -> {}/{}/{}".format(
            self.src_project_name,
            self.src_version_id,
            self.dst_project_name,
            self.dst_asset_id,
            self.dst_task_name
        )


class ProjectPushRepreItem:
    """Representation item.

    Args:
        repre_doc (Dict[str, Ant]): Representation document.
        roots (Dict[str, str]): Project roots (based on project anatomy).
    """

    def __init__(self, repre_doc, roots):
        self._repre_doc = repre_doc
        self._roots = roots
        self._src_files = None
        self._resource_files = None

    @property
    def repre_doc(self):
        return self._repre_doc

    @property
    def src_files(self):
        if self._src_files is None:
            self.get_source_files()
        return self._src_files

    @property
    def resource_files(self):
        if self._resource_files is None:
            self.get_source_files()
        return self._resource_files

    @staticmethod
    def validate_source_files(src_files, resource_files):
        if not src_files:
            raise AssertionError((
                "Couldn't figure out source files from representation."
                " Found resource files {}"
            ).format(", ".join(str(i) for i in resource_files)))

        invalid_items = [
            item
            for item in itertools.chain(src_files, resource_files)
            if not item.is_valid_file
        ]
        if invalid_items:
            raise AssertionError((
                "Source files that were not found on disk: {}"
            ).format(", ".join(str(i) for i in invalid_items)))

    def get_source_files(self):
        if self._src_files is not None:
            return self._src_files, self._resource_files

        repre_context = self._repre_doc["context"]
        if "frame" in repre_context or "udim" in repre_context:
            src_files, resource_files = self._get_source_files_with_frames()
        else:
            src_files, resource_files = self._get_source_files()

        self.validate_source_files(src_files, resource_files)

        self._src_files = src_files
        self._resource_files = resource_files
        return self._src_files, self._resource_files

    def _get_source_files_with_frames(self):
        frame_placeholder = "__frame__"
        udim_placeholder = "__udim__"
        src_files = []
        resource_files = []
        template = self._repre_doc["data"]["template"]
        repre_context = self._repre_doc["context"]
        fill_repre_context = copy.deepcopy(repre_context)
        if "frame" in fill_repre_context:
            fill_repre_context["frame"] = frame_placeholder

        if "udim" in fill_repre_context:
            fill_repre_context["udim"] = udim_placeholder

        fill_roots = fill_repre_context["root"]
        for root_name in tuple(fill_roots.keys()):
            fill_roots[root_name] = "{{root[{}]}}".format(root_name)
        repre_path = StringTemplate.format_template(template,
                                                    fill_repre_context)
        repre_path = repre_path.replace("\\", "/")
        src_dirpath, src_basename = os.path.split(repre_path)
        src_basename = (
            re.escape(src_basename)
            .replace(frame_placeholder, "(?P<frame>[0-9]+)")
            .replace(udim_placeholder, "(?P<udim>[0-9]+)")
        )
        src_basename_regex = re.compile("^{}$".format(src_basename))
        for file_info in self._repre_doc["files"]:
            filepath_template = file_info["path"].replace("\\", "/")
            filepath = filepath_template.format(root=self._roots)
            dirpath, basename = os.path.split(filepath_template)
            if dirpath != src_dirpath or not src_basename_regex.match(basename):
                relative_dir = dirpath.replace(src_dirpath, "")
                if relative_dir:
                    relative_path = "/".join([relative_dir, basename])
                else:
                    relative_path = basename
                resource_files.append(ResourceFile(filepath, relative_path))
                continue

            frame = None
            udim = None
            for item in src_basename_regex.finditer(basename):
                group_name = item.lastgroup
                value = item.group(group_name)
                if group_name == "frame":
                    frame = int(value)
                elif group_name == "udim":
                    udim = value

            src_files.append(SourceFile(filepath, frame, udim))

        return src_files, resource_files

    def _get_source_files(self):
        src_files = []
        resource_files = []
        template = self._repre_doc["data"]["template"]
        repre_context = self._repre_doc["context"]
        fill_repre_context = copy.deepcopy(repre_context)
        fill_roots = fill_repre_context["root"]
        for root_name in tuple(fill_roots.keys()):
            fill_roots[root_name] = "{{root[{}]}}".format(root_name)
        repre_path = StringTemplate.format_template(template,
                                                    fill_repre_context)
        repre_path = repre_path.replace("\\", "/")
        src_dirpath = os.path.dirname(repre_path)
        for file_info in self._repre_doc["files"]:
            filepath_template = file_info["path"].replace("\\", "/")
            filepath = filepath_template.format(root=self._roots)
            if filepath_template == repre_path:
                src_files.append(SourceFile(filepath))
            else:
                dirpath, basename = os.path.split(filepath_template)
                relative_dir = dirpath.replace(src_dirpath, "")
                if relative_dir:
                    relative_path = "/".join([relative_dir, basename])
                else:
                    relative_path = basename

                resource_files.append(
                    ResourceFile(filepath, relative_path)
                )
        return src_files, resource_files


class ProjectPushItemProcess:
    """
    Args:
        item (ProjectPushItem): Item which is being processed.
    """

    # TODO how to define 'variant'? - ask user
    variant = "Main"
    # TODO where to get host?!!!
    host_name = "republisher"

    def __init__(self, item):
        self._item = item
        self._src_project_doc = UNKNOWN
        self._src_asset_doc = UNKNOWN
        self._src_subset_doc = UNKNOWN
        self._src_version_doc = UNKNOWN
        self._src_repre_items = UNKNOWN
        self._src_anatomy = None

        self._project_doc = UNKNOWN
        self._anatomy = None
        self._asset_doc = UNKNOWN
        self._task_info = UNKNOWN
        self._subset_doc = None
        self._version_doc = None

        self._family = UNKNOWN
        self._subset_name = UNKNOWN

        self._project_settings = UNKNOWN
        self._template_name = UNKNOWN

        self._src_files = UNKNOWN
        self._src_resource_files = UNKNOWN

    def get_src_project_doc(self):
        if self._src_project_doc is UNKNOWN:
            self._src_project_doc = get_project(self._item.src_project_name)
        return self._src_project_doc

    def get_src_anatomy(self):
        if self._src_anatomy is None:
            self._src_anatomy = Anatomy(self._item.src_project_name)
        return self._src_anatomy

    def get_src_asset_doc(self):
        if self._src_asset_doc is UNKNOWN:
            asset_doc = None
            subset_doc = self.get_src_subset_doc()
            if subset_doc:
                asset_doc = get_asset_by_id(
                    self._item.src_project_name,
                    subset_doc["parent"]
                )
            self._src_asset_doc = asset_doc
        return self._src_asset_doc

    def get_src_subset_doc(self):
        if self._src_subset_doc is UNKNOWN:
            version_doc = self.get_src_version_doc()
            subset_doc = None
            if version_doc:
                subset_doc = get_subset_by_id(
                    self._item.src_project_name,
                    version_doc["parent"]
                )
            self._src_subset_doc = subset_doc
        return self._src_subset_doc

    def get_src_version_doc(self):
        if self._src_version_doc is UNKNOWN:
            self._src_version_doc = get_version_by_id(
                self._item.src_project_name, self._item.src_version_id
            )
        return self._src_version_doc

    def get_src_repre_items(self):
        if self._src_repre_items is UNKNOWN:
            repre_items = None
            version_doc = self.get_src_version_doc()
            if version_doc:
                repre_docs = get_representations(
                    self._item.src_project_name,
                    version_ids=[version_doc["_id"]]
                )
                repre_items = [
                    ProjectPushRepreItem(repre_doc, self.src_anatomy.roots)
                    for repre_doc in repre_docs
                ]
            self._src_repre_items = repre_items
        return self._src_repre_items

    src_project_doc = property(get_src_project_doc)
    src_anatomy = property(get_src_anatomy)
    src_asset_doc = property(get_src_asset_doc)
    src_subset_doc = property(get_src_subset_doc)
    src_version_doc = property(get_src_version_doc)
    src_repre_items = property(get_src_repre_items)

    def get_project_doc(self):
        if self._project_doc is UNKNOWN:
            self._project_doc = get_project(self._item.dst_project_name)
        return self._project_doc

    def get_anatomy(self):
        if self._anatomy is None:
            self._anatomy = Anatomy(self._item.dst_project_name)
        return self._anatomy

    def get_asset_doc(self):
        if self._asset_doc is UNKNOWN:
            self._asset_doc = get_asset_by_id(
                self._item.dst_project_name, self._item.dst_asset_id
            )
        return self._asset_doc

    def get_task_info(self):
        if self._task_info is UNKNOWN:
            task_name = self._item.dst_task_name
            if not task_name:
                self._task_info = {}
                return self._task_info

            project_doc = self.get_project_doc()
            asset_doc = self.get_asset_doc()
            if not project_doc or not asset_doc:
                self._task_info = None
                return self._task_info

            asset_tasks = asset_doc.get("data", {}).get("tasks") or {}
            task_info = asset_tasks.get(task_name)
            if not task_info:
                self._task_info = None
                return self._task_info

            # Create copy of task info to avoid changing data in asset document
            task_info = copy.deepcopy(task_info)
            task_info["name"] = task_name
            # Fill rest of task information based on task type
            task_type = task_info["type"]
            task_type_info = project_doc["config"]["tasks"].get(task_type, {})
            task_info.update(task_type_info)
            self._task_info = task_info

        return self._task_info

    def get_subset_doc(self):
        return self._subset_doc

    def set_subset_doc(self, subset_doc):
        self._subset_doc = subset_doc

    def get_version_doc(self):
        return self._version_doc

    def set_version_doc(self, version_doc):
        self._version_doc = version_doc

    project_doc = property(get_project_doc)
    anatomy = property(get_anatomy)
    asset_doc = property(get_asset_doc)
    task_info = property(get_task_info)
    subset_doc = property(get_subset_doc)
    version_doc = property(get_version_doc, set_version_doc)

    def get_project_settings(self):
        if self._project_settings is UNKNOWN:
            self._project_settings = get_project_settings(
                self._item.dst_project_name
            )
        return self._project_settings

    project_settings = property(get_project_settings)

    @property
    def family(self):
        if self._family is UNKNOWN:
            family = None
            subset_doc = self.src_subset_doc
            if subset_doc:
                family = subset_doc["data"].get("family")
                families = subset_doc["data"].get("families")
                if not family and families:
                    family = families[0]
            self._family = family
        return self._family

    @property
    def subset_name(self):
        if self._subset_name is UNKNOWN:
            subset_name = None
            family = self.family
            asset_doc = self.asset_doc
            task_info = self.task_info
            if family and asset_doc and task_info:
                subset_name = get_subset_name(
                    family,
                    self.variant,
                    task_info["name"],
                    asset_doc,
                    project_name=self._item.dst_project_name,
                    host_name=self.host_name,
                    project_settings=self.project_settings
                )
            self._subset_name = subset_name
        return self._subset_name

    @property
    def template_name(self):
        if self._template_name is UNKNOWN:
            task_info = self.task_info
            family = self.family
            template_name = None
            if family and task_info:
                template_name = get_publish_template_name(
                    self._item.dst_project_name,
                    self.host_name,
                    self.family,
                    task_info["name"],
                    task_info["type"],
                    project_settings=self.project_settings
                )
            self._template_name = template_name
        return self._template_name


class ProjectPushItemStatus:
    def __init__(
        self,
        item,
        failed=False,
        finished=False,
        error=None
    ):
        self._item = item
        self._failed = failed
        self._finished = finished
        self._error = error
        self._progress_messages = []
        self._last_message = None

    def get_failed(self):
        return self._failed

    def set_failed(self, failed):
        if failed == self._failed:
            return
        self._failed = failed

    def get_finished(self):
        return self._finished

    def set_finished(self, finished):
        if finished == self._finished:
            return
        self._finished = finished

    def get_error(self):
        return self._error

    def set_error(self, error, failed=None):
        if error == self._error:
            return
        self._error = error
        if failed is None:
            failed = error is not None

        if failed:
            self.failed = failed

    failed = property(get_failed, set_failed)
    finished = property(get_finished, set_finished)
    error = property(get_error, set_error)

    def add_progress_message(self, message):
        self._progress_messages.append(message)
        self._last_message = message
        print(message)

    @property
    def last_message(self):
        return self._last_message


class RepublisherController:
    def __init__(self):
        self._items = {}

    def add_item(self, item):
        if item.id in self._items:
            raise RepublishError(f"Item is already in queue {item}")
        self._items[item.id] = item

    def remote_item(self, item_id):
        self._items.pop(item_id, None)

    def get_items(self):
        return dict(self._items)


class FileItem(object):
    def __init__(self, path):
        self.path = path

    @property
    def is_valid_file(self):
        return os.path.exists(self.path) and os.path.isfile(self.path)


class SourceFile(FileItem):
    def __init__(self, path, frame=None, udim=None):
        super(SourceFile, self).__init__(path)
        self.frame = frame
        self.udim = udim

    def __repr__(self):
        subparts = [self.__class__.__name__]
        if self.frame is not None:
            subparts.append("frame: {}".format(self.frame))
        if self.udim is not None:
            subparts.append("UDIM: {}".format(self.udim))

        return "<{}> '{}'".format(" - ".join(subparts), self.path)


class ResourceFile(FileItem):
    def __init__(self, path, relative_path):
        super(ResourceFile, self).__init__(path)
        self.relative_path = relative_path

    def __repr__(self):
        return "<{}> '{}'".format(self.__class__.__name__, self.relative_path)


def _make_sure_subset_exists(item_process, project_name, operations):
    dst_asset_doc = item_process.asset_doc
    subset_name = item_process.subset_name
    family = item_process.family
    asset_id = dst_asset_doc["_id"]
    subset_doc = get_subset_by_name(project_name, subset_name, asset_id)
    if subset_doc:
        return subset_doc

    data = {
        "families": [family]
    }
    subset_doc = new_subset_document(
        subset_name, family, asset_id, data
    )
    operations.create_entity(project_name, "subset", subset_doc)
    item_process.set_subset_doc(subset_doc)


def _make_sure_version_exists(
    item_process,
    project_name,
    version,
    operations
):
    """Make sure version document exits in database.

    Args:
        item_process (ProjectPushItemProcess): Item handling process.
        project_name (str): Name of project where version should live.
        version (Union[int, None]): Number of version. Latest is used when
            'None' is passed.
        operations (OperationsSession): Session which handler creation and
            update of entities.

    Returns:
        Tuple[Dict[str, Any], bool]: New version document and boolean if version
            already existed in database.
    """

    src_version_doc = item_process.src_version_doc
    subset_doc = item_process.subset_doc
    subset_id = subset_doc["_id"]
    src_data = src_version_doc["data"]
    families = subset_doc["data"].get("families")
    if not families:
        families = [subset_doc["data"]["family"]]

    version_data = {
        "families": list(families),
        "fps": src_data.get("fps"),
        "source": src_data.get("source"),
        "machine": socket.gethostname(),
        "comment": "",
        "author": get_openpype_username(),
        "time": get_formatted_current_time(),
    }
    if version is None:
        last_version_doc = get_last_version_by_subset_id(
            project_name, subset_id
        )
        version = 1
        if last_version_doc:
            version += int(last_version_doc["name"])

    existing_version_doc = get_version_by_name(
        project_name, version, subset_id
    )
    # Update existing version
    if existing_version_doc:
        version_doc = new_version_doc(
            version, subset_id, version_data, existing_version_doc["_id"]
        )
        update_data = prepare_version_update_data(
            existing_version_doc, version_doc
        )
        if update_data:
            operations.update_entity(
                project_name,
                "version",
                existing_version_doc["_id"],
                update_data
            )
        item_process.set_version_doc(version_doc)

        return

    if version is None:
        last_version_doc = get_last_version_by_subset_id(
            project_name, subset_id
        )
        version = 1
        if last_version_doc:
            version += int(last_version_doc["name"])

    version_doc = new_version_doc(
        version, subset_id, version_data
    )
    operations.create_entity(project_name, "version", version_doc)

    item_process.set_version_doc(version_doc)


def _integrate_representations(item, item_process, item_status, operations):
    """

    Args:
        item (ProjectPushItem): Item to be pushed to different project.
        item_process (ProjectPushItemProcess): Process of push item.
    """

    version_id = item_process.version_doc["_id"]
    repre_names = {
        repre_item.repre_doc["name"]
        for repre_item in item_process.src_repre_items
    }
    existing_repres = get_representations(
        item.dst_project_name,
        representation_names=repre_names,
        version_ids=[version_id]
    )
    existing_repres_by_name = {
        repre_doc["name"] : repre_doc
        for repre_doc in existing_repres
    }
    anatomy = item_process.anatomy
    formatting_data = get_template_data(
        item_process.project_doc,
        item_process.asset_doc,
        item.dst_task_name,
        item_process.host_name
    )


def _republish_to(item, item_process, item_status):
    """

    Args:
        item (ProjectPushItem): Item to process.
        item_process (ProjectPushItemProcess): Item process information.
        item_status (ProjectPushItemStatus): Item status information.
    """

    family = item_process.family
    item_status.add_progress_message(
        f"Republishing family '{family}' (Based on source subset)"
    )

    subset_name = item_process.subset_name
    item_status.add_progress_message(f"Final subset name is '{subset_name}'")

    template_name = item_process.template_name
    item_status.add_progress_message(
        f"Using template '{template_name}' for integration"
    )

    repre_items = item_process.src_repre_items
    file_count = sum(
        len(repre_item.src_files) + len(repre_item.resource_files)
        for repre_item in repre_items
    )
    item_status.add_progress_message(
        f"Representation has {file_count} files to integrate"
    )

    operations = OperationsSession()
    item_status.add_progress_message(
        f"Integration to {item.dst_project_name} begins."
    )
    _make_sure_subset_exists(
        item_process,
        item.dst_project_name,
        operations
    )
    _make_sure_version_exists(
        item_process,
        item.dst_project_name,
        item.dst_version,
        operations
    )
    _integrate_representations(item, item_process, item_status, operations)


def _process_item(item, item_process, item_status):
    """

    Args:
        item (ProjectPushItem): Item defying the source and destination.
        item_process (ProjectPushItemProcess): Process item.
        item_status (ProjectPushItemStatus): Status of process item.
    """

    # Query all entities source and destination
    # - all of them are required for processing to exist
    # --- Source entities ---
    # Project - we just need validation of existence
    src_project_name = item.src_project_name
    src_project_doc = item_process.get_src_project_doc()
    if not src_project_doc:
        item_status.error = (
            f"Source project '{src_project_name}' was not found"
        )
        return
    item_status.add_progress_message(f"Project '{src_project_name}' found")

    # Representation - contains information of source files and template data
    repre_items = item_process.get_src_repre_items()
    if not repre_items:
        item_status.error = (
            f"Version {item.src_version_id} does not have any representations"
        )
        return

    item_status.add_progress_message(
        f"Found {len(repre_items)} representations on"
        f" version {item.src_version_id} in project '{src_project_name}'"
    )

    # --- Destination entities ---
    dst_project_name = item.dst_project_name
    dst_asset_id = item.dst_asset_id
    dst_task_name = item.dst_task_name

    # Validate project existence
    dst_project_doc = item_process.get_project_doc()
    if not dst_project_doc:
        item_status.error = (
            f"Destination project '{dst_project_name}' was not found"
        )
        return
    item_status.add_progress_message(f"Project '{dst_project_name}' found")

    # Get asset document
    if not item_process.asset_doc:
        item_status.error = (
            f"Destination asset with id '{dst_asset_id}'"
            f" was not found in project '{dst_project_name}'"
        )
        return
    item_status.add_progress_message((
        f"Asset with id '{dst_asset_id}'"
        f" found in project '{dst_project_name}'"
    ))

    # Get task information from asset document
    if not item_process.task_info:
        item_status.error = (
            f"Destination task '{dst_task_name}'"
            f" was not found on asset with id '{dst_asset_id}'"
            f" in project '{dst_project_name}'"
        )
        return

    item_status.add_progress_message((
        f"Task with name '{dst_task_name}'"
        f" found on asset with id '{dst_asset_id}'"
        f" in project '{dst_project_name}'"
    ))

    _republish_to(item, item_process, item_status)


def fake_process(controller):
    items = controller.get_items()
    for item in items.values():
        item_process = ProjectPushItemProcess(item)
        item_status = ProjectPushItemStatus(item)
        _process_item(item, item_process, item_status)
        if item_status.failed:
            print("Process failed")
        else:
            print("Process Finished")


def main():
    # NOTE For development purposes
    controller = RepublisherController()
    project_name = ""
    verssion_id = ""
    dst_project_name = ""
    dst_asset_id = ""
    dst_task_name = ""
    controller.add_item(ProjectPushItem(
        project_name,
        version_id,
        dst_project_name,
        dst_asset_id,
        dst_task_name,
        dst_version=1
    ))
    fake_process(controller)