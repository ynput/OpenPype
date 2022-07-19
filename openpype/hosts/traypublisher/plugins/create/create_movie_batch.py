import copy
import os
import re

from openpype.client import get_assets, get_asset_by_name
from openpype.hosts.traypublisher.api import pipeline
from openpype.lib import (
    FileDef,
    BoolDef,
    get_subset_name_with_asset_doc,
    TaskNotSetError,
)
from openpype.pipeline import (
    CreatedInstance,
    CreatorError
)

from openpype.hosts.traypublisher.api.plugin import TrayPublishCreator


class BatchMovieCreator(TrayPublishCreator):
    """Creates instances from movie file(s).

    Intended for .mov files, but should work for any video file.
    Doesn't handle image sequences though.
    """
    identifier = "render_movie_batch"
    label = "Batch Movies"
    family = "render"
    description = "Publish batch of video files"

    create_allow_context_change = False
    version_regex = re.compile(r"^(.+)_v([0-9]+)$")

    def __init__(self, project_settings, *args, **kwargs):
        super(BatchMovieCreator, self).__init__(project_settings,
                                              *args, **kwargs)
        creator_settings = (
            project_settings["traypublisher"]["BatchMovieCreator"]
        )
        self.default_variants = creator_settings["default_variants"]
        self.default_tasks = creator_settings["default_tasks"]
        self.extensions = creator_settings["extensions"]

    def get_icon(self):
        return "fa.file"

    def create(self, subset_name, data, pre_create_data):
        file_paths = pre_create_data.get("filepath")
        if not file_paths:
            return

        for file_info in file_paths:
            instance_data = copy.deepcopy(data)
            file_name = file_info["filenames"][0]
            filepath = os.path.join(file_info["directory"], file_name)
            instance_data["creator_attributes"] = {"filepath": filepath}

            asset_doc, version = self.get_asset_doc_from_file_name(
                file_name, self.project_name)

            subset_name, task_name = self._get_subset_and_task(
                asset_doc, data["variant"], self.project_name)

            instance_data["task"] = task_name
            instance_data["asset"] = asset_doc["name"]

            # Create new instance
            new_instance = CreatedInstance(self.family, subset_name,
                                           instance_data, self)
            self._store_new_instance(new_instance)

    def get_asset_doc_from_file_name(self, source_filename, project_name):
        """Try to parse out asset name from file name provided.

        Artists might provide various file name formats.
        Currently handled:
            - chair.mov
            - chair_v001.mov
            - my_chair_to_upload.mov
        """
        version = None
        asset_name = os.path.splitext(source_filename)[0]
        # Always first check if source filename is in assets
        matching_asset_doc = self._get_asset_by_name_case_not_sensitive(
            project_name, asset_name)

        if matching_asset_doc is None:
            matching_asset_doc, version = (
                self._parse_with_version(project_name, asset_name))

        if matching_asset_doc is None:
            matching_asset_doc = self._parse_containing(project_name,
                                                        asset_name)

        if matching_asset_doc is None:
            raise CreatorError(
                "Cannot guess asset name from {}".format(source_filename))

        return matching_asset_doc, version

    def _parse_with_version(self, project_name, asset_name):
        """Try to parse asset name from a file name containing version too

        Eg. 'chair_v001.mov' >> 'chair', 1
        """
        self.log.debug((
           "Asset doc by \"{}\" was not found, trying version regex."
        ).format(asset_name))

        matching_asset_doc = version_number = None

        regex_result = self.version_regex.findall(asset_name)
        if regex_result:
            _asset_name, _version_number = regex_result[0]
            matching_asset_doc = self._get_asset_by_name_case_not_sensitive(
                project_name, _asset_name)
            if matching_asset_doc:
                version_number = int(_version_number)

        return matching_asset_doc, version_number

    def _parse_containing(self, project_name, asset_name):
        """Look if file name contains any existing asset name"""
        for asset_doc in get_assets(project_name, fields=["name"]):
            if asset_doc["name"].lower() in asset_name.lower():
                return get_asset_by_name(project_name, asset_doc["name"])

    def _get_subset_and_task(self, asset_doc, variant, project_name):
        """Create subset name according to standard template process"""
        task_name = self._get_task_name(asset_doc)

        try:
            subset_name = get_subset_name_with_asset_doc(
                self.family,
                variant,
                task_name,
                asset_doc,
                project_name
            )
        except TaskNotSetError:
            # Create instance with fake task
            # - instance will be marked as invalid so it can't be published
            #   but user have ability to change it
            # NOTE: This expect that there is not task 'Undefined' on asset
            task_name = "Undefined"
            subset_name = get_subset_name_with_asset_doc(
                self.family,
                variant,
                task_name,
                asset_doc,
                project_name
            )

        return subset_name, task_name

    def _get_task_name(self, asset_doc):
        """Get applicable task from 'asset_doc' """
        available_task_names = {}
        asset_tasks = asset_doc.get("data", {}).get("tasks") or {}
        for task_name in asset_tasks.keys():
            available_task_names[task_name.lower()] = task_name

        task_name = None
        for _task_name in self.default_tasks:
            _task_name_low = _task_name.lower()
            if _task_name_low in available_task_names:
                task_name = available_task_names[_task_name_low]
                break

        return task_name

    def get_instance_attr_defs(self):
        return [
            BoolDef(
                "add_review_family",
                default=True,
                label="Review"
            )
        ]

    def get_pre_create_attr_defs(self):
        # Use same attributes as for instance attributes
        return [
            FileDef(
                "filepath",
                folders=False,
                single_item=False,
                extensions=self.extensions,
                label="Filepath"
            ),
            BoolDef(
                "add_review_family",
                default=True,
                label="Review"
            )
        ]

    def get_detail_description(self):
        return """# Publish batch of .mov to multiple assets.

        File names must then contain only asset name, or asset name + version.
        (eg. 'chair.mov', 'chair_v001.mov', not really safe `my_chair_v001.mov`
        """

    def _get_asset_by_name_case_not_sensitive(self, project_name, asset_name):
        """Handle more cases in file names"""
        asset_name = re.compile(asset_name, re.IGNORECASE)

        assets = list(get_assets(project_name, asset_names=[asset_name]))
        if assets:
            if len(assets) > 1:
                self.log.warning("Too many records found for {}".format(
                    asset_name))
                return

            return assets.pop()
