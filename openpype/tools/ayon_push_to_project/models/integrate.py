import os
import re
import copy
import socket
import itertools
import datetime
import sys
import traceback
import uuid

from bson.objectid import ObjectId

from openpype.client import (
    get_project,
    get_assets,
    get_asset_by_id,
    get_subset_by_id,
    get_subset_by_name,
    get_version_by_id,
    get_last_version_by_subset_id,
    get_version_by_name,
    get_representations,
)
from openpype.client.operations import (
    OperationsSession,
    new_asset_document,
    new_subset_document,
    new_version_doc,
    new_representation_doc,
    prepare_version_update_data,
    prepare_representation_update_data,
)
from openpype.modules import ModulesManager
from openpype.lib import (
    StringTemplate,
    get_openpype_username,
    get_formatted_current_time,
    source_hash,
)

from openpype.lib.file_transaction import FileTransaction
from openpype.settings import get_project_settings
from openpype.pipeline import Anatomy
from openpype.pipeline.version_start import get_versioning_start
from openpype.pipeline.template_data import get_template_data
from openpype.pipeline.publish import get_publish_template_name
from openpype.pipeline.create import get_subset_name

UNKNOWN = object()


class PushToProjectError(Exception):
    pass


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

    @property
    def is_valid_file(self):
        if not self.relative_path:
            return False
        return super(ResourceFile, self).is_valid_file


class ProjectPushItem:
    def __init__(
        self,
        src_project_name,
        src_version_id,
        dst_project_name,
        dst_folder_id,
        dst_task_name,
        variant,
        comment,
        new_folder_name,
        dst_version,
        item_id=None,
    ):
        if not item_id:
            item_id = uuid.uuid4().hex
        self.src_project_name = src_project_name
        self.src_version_id = src_version_id
        self.dst_project_name = dst_project_name
        self.dst_folder_id = dst_folder_id
        self.dst_task_name = dst_task_name
        self.dst_version = dst_version
        self.variant = variant
        self.new_folder_name = new_folder_name
        self.comment = comment or ""
        self.item_id = item_id
        self._repr_value = None

    @property
    def _repr(self):
        if not self._repr_value:
            self._repr_value = "|".join([
                self.src_project_name,
                self.src_version_id,
                self.dst_project_name,
                str(self.dst_folder_id),
                str(self.new_folder_name),
                str(self.dst_task_name),
                str(self.dst_version)
            ])
        return self._repr_value

    def __repr__(self):
        return "<{} - {}>".format(self.__class__.__name__, self._repr)

    def to_data(self):
        return {
            "src_project_name": self.src_project_name,
            "src_version_id": self.src_version_id,
            "dst_project_name": self.dst_project_name,
            "dst_folder_id": self.dst_folder_id,
            "dst_task_name": self.dst_task_name,
            "dst_version": self.dst_version,
            "variant": self.variant,
            "comment": self.comment,
            "new_folder_name": self.new_folder_name,
            "item_id": self.item_id,
        }

    @classmethod
    def from_data(cls, data):
        return cls(**data)


class StatusMessage:
    def __init__(self, message, level):
        self.message = message
        self.level = level

    def __str__(self):
        return "{}: {}".format(self.level.upper(), self.message)

    def __repr__(self):
        return "<{} - {}> {}".format(
            self.__class__.__name__, self.level.upper, self.message
        )


class ProjectPushItemStatus:
    def __init__(
        self,
        started=False,
        failed=False,
        finished=False,
        fail_reason=None,
        full_traceback=None
    ):
        self.started = started
        self.failed = failed
        self.finished = finished
        self.fail_reason = fail_reason
        self.full_traceback = full_traceback

    def set_failed(self, fail_reason, exc_info=None):
        """Set status as failed.

        Attribute 'fail_reason' can change automatically based on passed value.
        Reason is unset if 'failed' is 'False' and is set do default reason if
        is set to 'True' and reason is not set.

        Args:
            fail_reason (str): Reason why failed.
            exc_info(tuple): Exception info.
        """

        failed = True
        if not fail_reason and not exc_info:
            failed = False

        full_traceback = None
        if exc_info is not None:
            full_traceback = "".join(traceback.format_exception(*exc_info))
            if not fail_reason:
                fail_reason = "Failed without specified reason"

        self.failed = failed
        self.fail_reason = fail_reason or None
        self.full_traceback = full_traceback

    def to_data(self):
        return {
            "started": self.started,
            "failed": self.failed,
            "finished": self.finished,
            "fail_reason": self.fail_reason,
            "full_traceback": self.full_traceback,
        }

    @classmethod
    def from_data(cls, data):
        return cls(**data)


class ProjectPushRepreItem:
    """Representation item.

    Representation item based on representation document and project roots.

    Representation document may have reference to:
    - source files: Files defined with publish template
    - resource files: Files that should be in publish directory
        but filenames are not template based.

    Args:
        repre_doc (Dict[str, Ant]): Representation document.
        roots (Dict[str, str]): Project roots (based on project anatomy).
    """

    def __init__(self, repre_doc, roots):
        self._repre_doc = repre_doc
        self._roots = roots
        self._src_files = None
        self._resource_files = None
        self._frame = UNKNOWN

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
    def _clean_path(path):
        new_value = path.replace("\\", "/")
        while "//" in new_value:
            new_value = new_value.replace("//", "/")
        return new_value

    @staticmethod
    def _get_relative_path(path, src_dirpath):
        dirpath, basename = os.path.split(path)
        if not dirpath.lower().startswith(src_dirpath.lower()):
            return None

        relative_dir = dirpath[len(src_dirpath):].lstrip("/")
        if relative_dir:
            relative_path = "/".join([relative_dir, basename])
        else:
            relative_path = basename
        return relative_path

    @property
    def frame(self):
        """First frame of representation files.

        This value will be in representation document context if is sequence.

        Returns:
            Union[int, None]: First frame in representation files based on
                source files or None if frame is not part of filename.
        """

        if self._frame is UNKNOWN:
            frame = None
            for src_file in self.src_files:
                src_frame = src_file.frame
                if (
                    src_frame is not None
                    and (frame is None or src_frame < frame)
                ):
                    frame = src_frame
            self._frame = frame
        return self._frame

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
        # Remove padding from 'udim' and 'frame' formatting keys
        # - "{frame:0>4}" -> "{frame}"
        for key in ("udim", "frame"):
            sub_part = "{" + key + "[^}]*}"
            replacement = "{{{}}}".format(key)
            template = re.sub(sub_part, replacement, template)

        repre_context = self._repre_doc["context"]
        fill_repre_context = copy.deepcopy(repre_context)
        if "frame" in fill_repre_context:
            fill_repre_context["frame"] = frame_placeholder

        if "udim" in fill_repre_context:
            fill_repre_context["udim"] = udim_placeholder

        fill_roots = fill_repre_context["root"]
        for root_name in tuple(fill_roots.keys()):
            fill_roots[root_name] = "{{root[{}]}}".format(root_name)
        repre_path = StringTemplate.format_template(
            template, fill_repre_context)
        repre_path = self._clean_path(repre_path)
        src_dirpath, src_basename = os.path.split(repre_path)
        src_basename = (
            re.escape(src_basename)
            .replace(frame_placeholder, "(?P<frame>[0-9]+)")
            .replace(udim_placeholder, "(?P<udim>[0-9]+)")
        )
        src_basename_regex = re.compile("^{}$".format(src_basename))
        for file_info in self._repre_doc["files"]:
            filepath_template = self._clean_path(file_info["path"])
            filepath = self._clean_path(
                filepath_template.format(root=self._roots)
            )
            dirpath, basename = os.path.split(filepath_template)
            if (
                dirpath.lower() != src_dirpath.lower()
                or not src_basename_regex.match(basename)
            ):
                relative_path = self._get_relative_path(filepath, src_dirpath)
                resource_files.append(ResourceFile(filepath, relative_path))
                continue

            filepath = os.path.join(src_dirpath, basename)
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
        repre_path = self._clean_path(repre_path)
        src_dirpath = os.path.dirname(repre_path)
        for file_info in self._repre_doc["files"]:
            filepath_template = self._clean_path(file_info["path"])
            filepath = self._clean_path(
                filepath_template.format(root=self._roots))

            if filepath_template.lower() == repre_path.lower():
                src_files.append(
                    SourceFile(repre_path.format(root=self._roots))
                )
            else:
                relative_path = self._get_relative_path(
                    filepath_template, src_dirpath
                )
                resource_files.append(
                    ResourceFile(filepath, relative_path)
                )
        return src_files, resource_files


class ProjectPushItemProcess:
    """
    Args:
        model (IntegrateModel): Model which is processing item.
        item (ProjectPushItem): Item which is being processed.
    """

    # TODO where to get host?!!!
    host_name = "republisher"

    def __init__(self, model, item):
        self._model = model
        self._item = item

        self._src_asset_doc = None
        self._src_subset_doc = None
        self._src_version_doc = None
        self._src_repre_items = None

        self._project_doc = None
        self._anatomy = None
        self._asset_doc = None
        self._created_asset_doc = None
        self._task_info = None
        self._subset_doc = None
        self._version_doc = None

        self._family = None
        self._subset_name = None

        self._project_settings = None
        self._template_name = None

        self._status = ProjectPushItemStatus()
        self._operations = OperationsSession()
        self._file_transaction = FileTransaction()

        self._messages = []

    @property
    def item_id(self):
        return self._item.item_id

    @property
    def started(self):
        return self._status.started

    def get_status_data(self):
        return self._status.to_data()

    def integrate(self):
        self._status.started = True
        try:
            self._log_info("Process started")
            self._fill_source_variables()
            self._log_info("Source entities were found")
            self._fill_destination_project()
            self._log_info("Destination project was found")
            self._fill_or_create_destination_asset()
            self._log_info("Destination asset was determined")
            self._determine_family()
            self._determine_publish_template_name()
            self._determine_subset_name()
            self._make_sure_subset_exists()
            self._make_sure_version_exists()
            self._log_info("Prerequirements were prepared")
            self._integrate_representations()
            self._log_info("Integration finished")

        except PushToProjectError as exc:
            if not self._status.failed:
                self._status.set_failed(str(exc))

        except Exception as exc:
            _exc, _value, _tb = sys.exc_info()
            self._status.set_failed(
                "Unhandled error happened: {}".format(str(exc)),
                (_exc, _value, _tb)
            )

        finally:
            self._status.finished = True
            self._emit_event(
                "push.finished.changed",
                {
                    "finished": True,
                    "item_id": self.item_id,
                }
            )

    def _emit_event(self, topic, data):
        self._model.emit_event(topic, data)

    # Loggin helpers
    # TODO better logging
    def _add_message(self, message, level):
        message_obj = StatusMessage(message, level)
        self._messages.append(message_obj)
        self._emit_event(
            "push.message.added",
            {
                "message": message,
                "level": level,
                "item_id": self.item_id,
            }
        )
        print(message_obj)
        return message_obj

    def _log_debug(self, message):
        return self._add_message(message, "debug")

    def _log_info(self, message):
        return self._add_message(message, "info")

    def _log_warning(self, message):
        return self._add_message(message, "warning")

    def _log_error(self, message):
        return self._add_message(message, "error")

    def _log_critical(self, message):
        return self._add_message(message, "critical")

    def _fill_source_variables(self):
        src_project_name = self._item.src_project_name
        src_version_id = self._item.src_version_id

        project_doc = get_project(src_project_name)
        if not project_doc:
            self._status.set_failed(
                f"Source project \"{src_project_name}\" was not found"
            )

            self._emit_event(
                "push.failed.changed",
                {"item_id": self.item_id}
            )
            raise PushToProjectError(self._status.fail_reason)

        self._log_debug(f"Project '{src_project_name}' found")

        version_doc = get_version_by_id(src_project_name, src_version_id)
        if not version_doc:
            self._status.set_failed((
                f"Source version with id \"{src_version_id}\""
                f" was not found in project \"{src_project_name}\""
            ))
            raise PushToProjectError(self._status.fail_reason)

        subset_id = version_doc["parent"]
        subset_doc = get_subset_by_id(src_project_name, subset_id)
        if not subset_doc:
            self._status.set_failed((
                f"Could find subset with id \"{subset_id}\""
                f" in project \"{src_project_name}\""
            ))
            raise PushToProjectError(self._status.fail_reason)

        asset_id = subset_doc["parent"]
        asset_doc = get_asset_by_id(src_project_name, asset_id)
        if not asset_doc:
            self._status.set_failed((
                f"Could find asset with id \"{asset_id}\""
                f" in project \"{src_project_name}\""
            ))
            raise PushToProjectError(self._status.fail_reason)

        anatomy = Anatomy(src_project_name)

        repre_docs = get_representations(
            src_project_name,
            version_ids=[src_version_id]
        )
        repre_items = [
            ProjectPushRepreItem(repre_doc, anatomy.roots)
            for repre_doc in repre_docs
        ]
        self._log_debug((
            f"Found {len(repre_items)} representations on"
            f" version {src_version_id} in project '{src_project_name}'"
        ))
        if not repre_items:
            self._status.set_failed(
                "Source version does not have representations"
                f" (Version id: {src_version_id})"
            )
            raise PushToProjectError(self._status.fail_reason)

        self._src_asset_doc = asset_doc
        self._src_subset_doc = subset_doc
        self._src_version_doc = version_doc
        self._src_repre_items = repre_items

    def _fill_destination_project(self):
        # --- Destination entities ---
        dst_project_name = self._item.dst_project_name
        # Validate project existence
        dst_project_doc = get_project(dst_project_name)
        if not dst_project_doc:
            self._status.set_failed(
                f"Destination project '{dst_project_name}' was not found"
            )
            raise PushToProjectError(self._status.fail_reason)

        self._log_debug(
            f"Destination project '{dst_project_name}' found"
        )
        self._project_doc = dst_project_doc
        self._anatomy = Anatomy(dst_project_name)
        self._project_settings = get_project_settings(
            self._item.dst_project_name
        )

    def _create_asset(
        self,
        src_asset_doc,
        project_doc,
        parent_asset_doc,
        asset_name
    ):
        parent_id = None
        parents = []
        tools = []
        if parent_asset_doc:
            parent_id = parent_asset_doc["_id"]
            parents = list(parent_asset_doc["data"]["parents"])
            parents.append(parent_asset_doc["name"])
            _tools = parent_asset_doc["data"].get("tools_env")
            if _tools:
                tools = list(_tools)

        asset_name_low = asset_name.lower()
        other_asset_docs = get_assets(
            project_doc["name"], fields=["_id", "name", "data.visualParent"]
        )
        for other_asset_doc in other_asset_docs:
            other_name = other_asset_doc["name"]
            other_parent_id = other_asset_doc["data"].get("visualParent")
            if other_name.lower() != asset_name_low:
                continue

            if other_parent_id != parent_id:
                self._status.set_failed((
                    f"Asset with name \"{other_name}\" already"
                    " exists in different hierarchy."
                ))
                raise PushToProjectError(self._status.fail_reason)

            self._log_debug((
                f"Found already existing asset with name \"{other_name}\""
                f" which match requested name \"{asset_name}\""
            ))
            return get_asset_by_id(project_doc["name"], other_asset_doc["_id"])

        data_keys = (
            "clipIn",
            "clipOut",
            "frameStart",
            "frameEnd",
            "handleStart",
            "handleEnd",
            "resolutionWidth",
            "resolutionHeight",
            "fps",
            "pixelAspect",
        )
        asset_data = {
            "visualParent": parent_id,
            "parents": parents,
            "tasks": {},
            "tools_env": tools
        }
        src_asset_data = src_asset_doc["data"]
        for key in data_keys:
            if key in src_asset_data:
                asset_data[key] = src_asset_data[key]

        asset_doc = new_asset_document(
            asset_name,
            project_doc["_id"],
            parent_id,
            parents,
            data=asset_data
        )
        self._operations.create_entity(
            project_doc["name"],
            asset_doc["type"],
            asset_doc
        )
        self._log_info(
            f"Creating new asset with name \"{asset_name}\""
        )
        self._created_asset_doc = asset_doc
        return asset_doc

    def _fill_or_create_destination_asset(self):
        dst_project_name = self._item.dst_project_name
        dst_folder_id = self._item.dst_folder_id
        dst_task_name = self._item.dst_task_name
        new_folder_name = self._item.new_folder_name
        if not dst_folder_id and not new_folder_name:
            self._status.set_failed(
                "Push item does not have defined destination asset"
            )
            raise PushToProjectError(self._status.fail_reason)

        # Get asset document
        parent_asset_doc = None
        if dst_folder_id:
            parent_asset_doc = get_asset_by_id(
                self._item.dst_project_name, self._item.dst_folder_id
            )
            if not parent_asset_doc:
                self._status.set_failed(
                    f"Could find asset with id \"{dst_folder_id}\""
                    f" in project \"{dst_project_name}\""
                )
                raise PushToProjectError(self._status.fail_reason)

        if not new_folder_name:
            asset_doc = parent_asset_doc
        else:
            asset_doc = self._create_asset(
                self._src_asset_doc,
                self._project_doc,
                parent_asset_doc,
                new_folder_name
            )
        self._asset_doc = asset_doc
        if not dst_task_name:
            self._task_info = {}
            return

        asset_path_parts = list(asset_doc["data"]["parents"])
        asset_path_parts.append(asset_doc["name"])
        asset_path = "/".join(asset_path_parts)
        asset_tasks = asset_doc.get("data", {}).get("tasks") or {}
        task_info = asset_tasks.get(dst_task_name)
        if not task_info:
            self._status.set_failed(
                f"Could find task with name \"{dst_task_name}\""
                f" on asset \"{asset_path}\""
                f" in project \"{dst_project_name}\""
            )
            raise PushToProjectError(self._status.fail_reason)

        # Create copy of task info to avoid changing data in asset document
        task_info = copy.deepcopy(task_info)
        task_info["name"] = dst_task_name
        # Fill rest of task information based on task type
        task_type = task_info["type"]
        task_type_info = self._project_doc["config"]["tasks"].get(
            task_type, {})
        task_info.update(task_type_info)
        self._task_info = task_info

    def _determine_family(self):
        subset_doc = self._src_subset_doc
        family = subset_doc["data"].get("family")
        families = subset_doc["data"].get("families")
        if not family and families:
            family = families[0]

        if not family:
            self._status.set_failed(
                "Couldn't figure out family from source subset"
            )
            raise PushToProjectError(self._status.fail_reason)

        self._log_debug(
            f"Publishing family is '{family}' (Based on source subset)"
        )
        self._family = family

    def _determine_publish_template_name(self):
        template_name = get_publish_template_name(
            self._item.dst_project_name,
            self.host_name,
            self._family,
            self._task_info.get("name"),
            self._task_info.get("type"),
            project_settings=self._project_settings
        )
        self._log_debug(
            f"Using template '{template_name}' for integration"
        )
        self._template_name = template_name

    def _determine_subset_name(self):
        family = self._family
        asset_doc = self._asset_doc
        task_info = self._task_info
        subset_name = get_subset_name(
            family,
            self._item.variant,
            task_info.get("name"),
            asset_doc,
            project_name=self._item.dst_project_name,
            host_name=self.host_name,
            project_settings=self._project_settings
        )
        self._log_info(
            f"Push will be integrating to subset with name '{subset_name}'"
        )
        self._subset_name = subset_name

    def _make_sure_subset_exists(self):
        project_name = self._item.dst_project_name
        asset_id = self._asset_doc["_id"]
        subset_name = self._subset_name
        family = self._family
        subset_doc = get_subset_by_name(project_name, subset_name, asset_id)
        if subset_doc:
            self._subset_doc = subset_doc
            return subset_doc

        data = {
            "families": [family]
        }
        subset_doc = new_subset_document(
            subset_name, family, asset_id, data
        )
        self._operations.create_entity(project_name, "subset", subset_doc)
        self._subset_doc = subset_doc

    def _make_sure_version_exists(self):
        """Make sure version document exits in database."""

        project_name = self._item.dst_project_name
        version = self._item.dst_version
        src_version_doc = self._src_version_doc
        subset_doc = self._subset_doc
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
            "comment": self._item.comment or "",
            "author": get_openpype_username(),
            "time": get_formatted_current_time(),
        }
        if version is None:
            last_version_doc = get_last_version_by_subset_id(
                project_name, subset_id
            )
            if last_version_doc:
                version = int(last_version_doc["name"]) + 1
            else:
                version = get_versioning_start(
                    project_name,
                    self.host_name,
                    task_name=self._task_info["name"],
                    task_type=self._task_info["type"],
                    family=families[0],
                    subset=subset_doc["name"]
                )

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
                self._operations.update_entity(
                    project_name,
                    "version",
                    existing_version_doc["_id"],
                    update_data
                )
            self._version_doc = version_doc

            return

        version_doc = new_version_doc(
            version, subset_id, version_data
        )
        self._operations.create_entity(project_name, "version", version_doc)

        self._version_doc = version_doc

    def _integrate_representations(self):
        try:
            self._real_integrate_representations()
        except Exception:
            self._operations.clear()
            self._file_transaction.rollback()
            raise

    def _real_integrate_representations(self):
        version_doc = self._version_doc
        version_id = version_doc["_id"]
        existing_repres = get_representations(
            self._item.dst_project_name,
            version_ids=[version_id]
        )
        existing_repres_by_low_name = {
            repre_doc["name"].lower(): repre_doc
            for repre_doc in existing_repres
        }
        template_name = self._template_name
        anatomy = self._anatomy
        formatting_data = get_template_data(
            self._project_doc,
            self._asset_doc,
            self._task_info.get("name"),
            self.host_name
        )
        formatting_data.update({
            "subset": self._subset_name,
            "family": self._family,
            "version": version_doc["name"]
        })

        path_template = anatomy.templates[template_name]["path"].replace(
            "\\", "/"
        )
        file_template = StringTemplate(
            anatomy.templates[template_name]["file"]
        )
        self._log_info("Preparing files to transfer")
        processed_repre_items = self._prepare_file_transactions(
            anatomy, template_name, formatting_data, file_template
        )
        self._file_transaction.process()
        self._log_info("Preparing database changes")
        self._prepare_database_operations(
            version_id,
            processed_repre_items,
            path_template,
            existing_repres_by_low_name
        )
        self._log_info("Finalization")
        self._operations.commit()
        self._file_transaction.finalize()

    def _prepare_file_transactions(
        self, anatomy, template_name, formatting_data, file_template
    ):
        processed_repre_items = []
        for repre_item in self._src_repre_items:
            repre_doc = repre_item.repre_doc
            repre_name = repre_doc["name"]
            repre_format_data = copy.deepcopy(formatting_data)
            repre_format_data["representation"] = repre_name
            for src_file in repre_item.src_files:
                ext = os.path.splitext(src_file.path)[-1]
                repre_format_data["ext"] = ext[1:]
                break

            # Re-use 'output' from source representation
            repre_output_name = repre_doc["context"].get("output")
            if repre_output_name is not None:
                repre_format_data["output"] = repre_output_name

            template_obj = anatomy.templates_obj[template_name]["folder"]
            folder_path = template_obj.format_strict(formatting_data)
            repre_context = folder_path.used_values
            folder_path_rootless = folder_path.rootless
            repre_filepaths = []
            published_path = None
            for src_file in repre_item.src_files:
                file_data = copy.deepcopy(repre_format_data)
                frame = src_file.frame
                if frame is not None:
                    file_data["frame"] = frame

                udim = src_file.udim
                if udim is not None:
                    file_data["udim"] = udim

                filename = file_template.format_strict(file_data)
                dst_filepath = os.path.normpath(
                    os.path.join(folder_path, filename)
                )
                dst_rootless_path = os.path.normpath(
                    os.path.join(folder_path_rootless, filename)
                )
                if published_path is None or frame == repre_item.frame:
                    published_path = dst_filepath
                    repre_context.update(filename.used_values)

                repre_filepaths.append((dst_filepath, dst_rootless_path))
                self._file_transaction.add(src_file.path, dst_filepath)

            for resource_file in repre_item.resource_files:
                dst_filepath = os.path.normpath(
                    os.path.join(folder_path, resource_file.relative_path)
                )
                dst_rootless_path = os.path.normpath(
                    os.path.join(
                        folder_path_rootless, resource_file.relative_path
                    )
                )
                repre_filepaths.append((dst_filepath, dst_rootless_path))
                self._file_transaction.add(resource_file.path, dst_filepath)
            processed_repre_items.append(
                (repre_item, repre_filepaths, repre_context, published_path)
            )
        return processed_repre_items

    def _prepare_database_operations(
        self,
        version_id,
        processed_repre_items,
        path_template,
        existing_repres_by_low_name
    ):
        modules_manager = ModulesManager()
        sync_server_module = modules_manager.get("sync_server")
        if sync_server_module is None or not sync_server_module.enabled:
            sites = [{
                "name": "studio",
                "created_dt": datetime.datetime.now()
            }]
        else:
            sites = sync_server_module.compute_resource_sync_sites(
                project_name=self._item.dst_project_name
            )

        added_repre_names = set()
        for item in processed_repre_items:
            (repre_item, repre_filepaths, repre_context, published_path) = item
            repre_name = repre_item.repre_doc["name"]
            added_repre_names.add(repre_name.lower())
            new_repre_data = {
                "path": published_path,
                "template": path_template
            }
            new_repre_files = []
            for (path, rootless_path) in repre_filepaths:
                new_repre_files.append({
                    "_id": ObjectId(),
                    "path": rootless_path,
                    "size": os.path.getsize(path),
                    "hash": source_hash(path),
                    "sites": sites
                })

            existing_repre = existing_repres_by_low_name.get(
                repre_name.lower()
            )
            entity_id = None
            if existing_repre:
                entity_id = existing_repre["_id"]
            new_repre_doc = new_representation_doc(
                repre_name,
                version_id,
                repre_context,
                data=new_repre_data,
                entity_id=entity_id
            )
            new_repre_doc["files"] = new_repre_files
            if not existing_repre:
                self._operations.create_entity(
                    self._item.dst_project_name,
                    new_repre_doc["type"],
                    new_repre_doc
                )
            else:
                update_data = prepare_representation_update_data(
                    existing_repre, new_repre_doc
                )
                if update_data:
                    self._operations.update_entity(
                        self._item.dst_project_name,
                        new_repre_doc["type"],
                        new_repre_doc["_id"],
                        update_data
                    )

        existing_repre_names = set(existing_repres_by_low_name.keys())
        for repre_name in (existing_repre_names - added_repre_names):
            repre_doc = existing_repres_by_low_name[repre_name]
            self._operations.update_entity(
                self._item.dst_project_name,
                repre_doc["type"],
                repre_doc["_id"],
                {"type": "archived_representation"}
            )


class IntegrateModel:
    def __init__(self, controller):
        self._controller = controller
        self._process_items = {}

    def reset(self):
        self._process_items = {}

    def emit_event(self, topic, data=None, source=None):
        self._controller.emit_event(topic, data, source)

    def create_process_item(
        self,
        src_project_name,
        src_version_id,
        dst_project_name,
        dst_folder_id,
        dst_task_name,
        variant,
        comment,
        new_folder_name,
        dst_version,
    ):
        """Create new item for integration.

        Args:
            src_project_name (str): Source project name.
            src_version_id (str): Source version id.
            dst_project_name (str): Destination project name.
            dst_folder_id (str): Destination folder id.
            dst_task_name (str): Destination task name.
            variant (str): Variant name.
            comment (Union[str, None]): Comment.
            new_folder_name (Union[str, None]): New folder name.
            dst_version (int): Destination version number.

        Returns:
            str: Item id. The id can be used to trigger integration or get
                status information.
        """

        item = ProjectPushItem(
            src_project_name,
            src_version_id,
            dst_project_name,
            dst_folder_id,
            dst_task_name,
            variant,
            comment=comment,
            new_folder_name=new_folder_name,
            dst_version=dst_version
        )
        process_item = ProjectPushItemProcess(self, item)
        self._process_items[item.item_id] = process_item
        return item.item_id

    def integrate_item(self, item_id):
        """Start integration of item.

        Args:
            item_id (str): Item id which should be integrated.
        """

        item = self._process_items.get(item_id)
        if item is None or item.started:
            return
        item.integrate()

    def get_item_status(self, item_id):
        """Status of an item.

        Args:
            item_id (str): Item id for which status should be returned.

        Returns:
            dict[str, Any]: Status data.
        """

        item = self._process_items.get(item_id)
        if item is not None:
            return item.get_status_data()
        return None
