import copy
import os
import re

from openpype import AYON_SERVER_ENABLED
from openpype.client import get_asset_name_identifier
from openpype.lib import (
    FileDef,
    BoolDef,
)
from openpype.pipeline import (
    CreatedInstance,
)
from openpype.pipeline.create import (
    get_subset_name,
    TaskNotSetError,
)

from openpype.hosts.traypublisher.api.plugin import TrayPublishCreator
from openpype.hosts.traypublisher.batch_parsing import (
    get_asset_doc_from_file_name
)


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
    # Position batch creator after simple creators
    order = 110

    def apply_settings(self, project_settings):
        creator_settings = (
            project_settings["traypublisher"]["create"]["BatchMovieCreator"]
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

            asset_doc, version = get_asset_doc_from_file_name(
                file_name, self.project_name, self.version_regex)

            subset_name, task_name = self._get_subset_and_task(
                asset_doc, data["variant"], self.project_name)

            asset_name = get_asset_name_identifier(asset_doc)

            instance_data["task"] = task_name
            if AYON_SERVER_ENABLED:
                instance_data["folderPath"] = asset_name
            else:
                instance_data["asset"] = asset_name

            # Create new instance
            new_instance = CreatedInstance(self.family, subset_name,
                                           instance_data, self)
            self._store_new_instance(new_instance)

    def _get_subset_and_task(self, asset_doc, variant, project_name):
        """Create subset name according to standard template process"""
        task_name = self._get_task_name(asset_doc)

        try:
            subset_name = get_subset_name(
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
            subset_name = get_subset_name(
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
                allow_sequences=False,
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
