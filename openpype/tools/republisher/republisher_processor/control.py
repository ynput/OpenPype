import os
import re
import copy
import requests
from openpype.client import (
    get_project,
    get_asset_by_id,
    get_subset_by_name,
    get_representation_by_id,
    get_representation_parents,
)
from openpype.lib import StringTemplate
from openpype.settings import get_project_settings
from openpype.pipeline.publish import get_publish_template_name
from openpype.pipeline.create import get_subset_name


class RepublishError(Exception):
    pass


class RepublishItem:
    def __init__(
        self,
        src_project_name,
        src_representation_id,
        dst_project_name,
        dst_asset_id,
        dst_task_name,
        dst_version=None
    ):
        self.src_project_name = src_project_name
        self.src_representation_id = src_representation_id
        self.dst_project_name = dst_project_name
        self.dst_asset_id = dst_asset_id
        self.dst_task_name = dst_task_name
        self.dst_version = dst_version
        self._id = "|".join([
            src_project_name,
            src_representation_id,
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
            self.src_representation_id,
            self.dst_project_name,
            self.dst_asset_id,
            self.dst_task_name
        )


class RepublishItemStatus:
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


class SourceFile:
    def __init__(self, path, frame=None, udim=None):
        self.path = path
        self.frame = frame
        self.udim = udim

    def __repr__(self):
        subparts = [self.__class__.__name__]
        if self.frame is not None:
            subparts.append("frame: {}".format(self.frame))
        if self.udim is not None:
            subparts.append("UDIM: {}".format(self.udim))

        return "<{}> '{}'".format(" - ".join(subparts), self.path)


class ResourceFile:
    def __init__(self, path, relative_path):
        self.path = path
        self.relative_path = relative_path

    def __repr__(self):
        return "<{}> '{}'".format(self.__class__.__name__, self.relative_path)


def get_source_files_with_frames(src_representation):
    frame_placeholder = "__frame__"
    udim_placeholder = "__udim__"
    src_files = []
    resource_files = []
    template = src_representation["data"]["template"]
    repre_context = src_representation["context"]
    fill_repre_context = copy.deepcopy(repre_context)
    if "frame" in fill_repre_context:
        fill_repre_context["frame"] = frame_placeholder

    if "udim" in fill_repre_context:
        fill_repre_context["udim"] = udim_placeholder

    fill_roots = fill_repre_context["root"]
    for root_name in tuple(fill_roots.keys()):
        fill_roots[root_name] = "{{root[{}]}}".format(root_name)
    repre_path = StringTemplate.format_template(template, fill_repre_context)
    repre_path = repre_path.replace("\\", "/")
    src_dirpath, src_basename = os.path.split(repre_path)
    src_basename = (
        re.escape(src_basename)
        .replace(frame_placeholder, "(?P<frame>[0-9]+)")
        .replace(udim_placeholder, "(?P<udim>[0-9]+)")
    )
    src_basename_regex = re.compile("^{}$".format(src_basename))
    for file_info in src_representation["files"]:
        filepath = file_info["path"].replace("\\", "/")
        dirpath, basename = os.path.split(filepath)
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


def get_source_files(src_representation):
    repre_context = src_representation["context"]
    if "frame" in repre_context or "udim" in repre_context:
        return get_source_files_with_frames(src_representation)

    src_files = []
    resource_files = []
    template = src_representation["data"]["template"]
    fill_repre_context = copy.deepcopy(repre_context)
    fill_roots = fill_repre_context["root"]
    for root_name in tuple(fill_roots.keys()):
        fill_roots[root_name] = "{{root[{}]}}".format(root_name)
    repre_path = StringTemplate.format_template(template, fill_repre_context)
    repre_path = repre_path.replace("\\", "/")
    src_dirpath = os.path.dirname(repre_path)
    for file_info in src_representation["files"]:
        filepath = file_info["path"]
        if filepath == repre_path:
            src_files.append(SourceFile(filepath))
        else:
            dirpath, basename = os.path.split(filepath)
            relative_dir = dirpath.replace(src_dirpath, "")
            if relative_dir:
                relative_path = "/".join([relative_dir, basename])
            else:
                relative_path = basename
            resource_files.append(ResourceFile(filepath, relative_path))
    return src_files, resource_files


def _republish_to(
    item,
    item_process,
    src_representation,
    src_representation_parents,
    dst_asset_doc,
    dst_task_info
):
    """

    Args:
        item (RepublishItem): Item to process.
        item_process (RepublishItemStatus): Item process information.
        src_representation (Dict[str, Any]): Representation document.
        src_representation_parents (Tuple[Any, Any, Any, Any]): Representation
            parent documents.
        dst_asset_doc (Dict[str, Any]): Asset document as destination of
            publishing.
        dst_task_info (Dict[str, str]): Task information with prepared
            infromation from project config.
    """

    src_subset_doc = src_representation_parents[1]
    family = src_subset_doc["data"].get("family")
    if not family:
        families = src_subset_doc["data"]["families"]
        family = families[0]

    item_process.add_progress_message(
        f"Republishing family '{family}' (Based on source subset)"
    )
    # TODO how to define 'variant'?
    variant = "Main"
    # TODO where to get host?
    host_name = "republisher"
    project_settings = get_project_settings(item.dst_project_name)

    subset_name = get_subset_name(
        family,
        variant,
        dst_task_info["name"],
        dst_asset_doc,
        project_name=item.dst_project_name,
        host_name=host_name,
        project_settings=project_settings
    )
    item_process.add_progress_message(f"Final subset name is '{subset_name}'")

    template_name = get_publish_template_name(
        item.dst_project_name,
        host_name,
        family,
        dst_task_info["name"],
        dst_task_info["type"],
        project_settings=project_settings
    )
    item_process.add_progress_message(
        f"Using template '{template_name}' for integration"
    )

    src_files, resource_files = get_source_files(src_representation)


def _process_item(item, item_process):
    # Query all entities source and destination
    # - all of them are required for processing to exist
    # --- Source entities ---
    # Project - we just need validation of existence
    src_project_name = item.src_project_name
    src_project_doc = get_project(src_project_name, fields=["name"])
    if not src_project_doc:
        item_process.error = (
            f"Source project '{src_project_name}' was not found"
        )
        return
    item_process.add_progress_message(f"Project '{src_project_name}' found")

    # Representation - contains information of source files and template data
    src_representation_id = item.src_representation_id
    src_representation = get_representation_by_id(
        src_project_name, src_representation_id
    )
    if not src_representation:
        item_process.error = (
            f"Representation with id '{src_representation_id}'"
            f" was not found in project '{src_project_name}'"
        )
        return
    item_process.add_progress_message(
        f"Representation with id '{src_representation_id}' found"
        f" in project '{src_project_name}'"
    )

    # --- Destination entities ---
    dst_project_name = item.dst_project_name
    dst_asset_id = item.dst_asset_id
    dst_task_name = item.dst_task_name

    # Validate project existence
    dst_project_doc = get_project(dst_project_name, fields=["name", "config"])
    if not dst_project_doc:
        item_process.error = (
            f"Destination project '{dst_project_name}' was not found"
        )
        return
    item_process.add_progress_message(f"Project '{dst_project_name}' found")

    # Get asset document
    dst_asset_doc = get_asset_by_id(
        dst_project_name,
        dst_asset_id
    )
    if not dst_asset_doc:
        item_process.error = (
            f"Destination asset with id '{dst_asset_id}'"
            f" was not found in project '{dst_project_name}'"
        )
        return
    item_process.add_progress_message((
        f"Asset with id '{dst_asset_id}'"
        f" found in project '{dst_project_name}'"
    ))

    # Get task information from asset document
    asset_tasks = dst_asset_doc.get("data", {}).get("tasks") or {}
    task_info = asset_tasks.get(dst_task_name)
    if not task_info:
        item_process.error = (
            f"Destination task '{dst_task_name}'"
            f" was not found on asset with id '{dst_asset_id}'"
            f" in project '{dst_project_name}'"
        )
        return

    item_process.add_progress_message((
        f"Task with name '{dst_task_name}'"
        f" found on asset with id '{dst_asset_id}'"
        f" in project '{dst_project_name}'"
    ))
    # Create copy of task info to avoid changing data in asset document
    dst_task_info = copy.deepcopy(task_info)
    dst_task_info["name"] = dst_task_name
    # Fill rest of task information based on task type
    task_type = dst_task_info["type"]
    task_type_info = dst_project_doc["config"]["tasks"].get(task_type)
    dst_task_info.update(task_type_info)

    src_representation_parents = get_representation_parents(
        src_project_name, src_representation
    )
    _republish_to(
        item,
        item_process,
        src_representation,
        src_representation_parents,
        dst_asset_doc,
        dst_task_info
    )


def fake_process(controller):
    items = controller.get_items()
    for item in items.values():
        item_process = RepublishItemStatus(item)
        _process_item(item, item_process)
        if item_process.failed:
            print("Process failed")
        else:
            print("Process Finished")


def main():
    # NOTE For development purposes
    controller = RepublisherController()
    project_name = ""
    representation_id = ""
    dst_project_name = ""
    dst_asset_id = ""
    dst_task_name = ""
    controller.add_item(RepublishItem(
        project_name,
        representation_id,
        dst_project_name,
        dst_asset_id,
        dst_task_name
    ))
    fake_process(controller)