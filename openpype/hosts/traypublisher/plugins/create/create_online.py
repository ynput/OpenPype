# -*- coding: utf-8 -*-
"""Creator of online files.

Online file retain their original name and use it as subset name. To
avoid conflicts, this creator checks if subset with this name already
exists under selected asset.
"""
from pathlib import Path

# from openpype.client import get_subset_by_name, get_asset_by_name
from openpype.lib.attribute_definitions import FileDef, BoolDef
from openpype.pipeline import (
    CreatedInstance,
    CreatorError
)
from openpype.hosts.traypublisher.api.plugin import TrayPublishCreator


class OnlineCreator(TrayPublishCreator):
    """Creates instance from file and retains its original name."""

    identifier = "io.openpype.creators.traypublisher.online"
    label = "Online"
    family = "online"
    description = "Publish file retaining its original file name"
    extensions = [".mov", ".mp4", ".mxf", ".m4v", ".mpg", ".exr",
                  ".dpx", ".tif", ".png", ".jpg"]

    def get_detail_description(self):
        return """# Create file retaining its original file name.

        This will publish files using template helping to retain original
        file name and that file name is used as subset name.

        Bz default it tries to guard against multiple publishes of the same
        file."""

    def get_icon(self):
        return "fa.file"

    def create(self, subset_name, instance_data, pre_create_data):
        repr_file = pre_create_data.get("representation_file")
        if not repr_file:
            raise CreatorError("No files specified")

        files = repr_file.get("filenames")
        if not files:
            # this should never happen
            raise CreatorError("Missing files from representation")

        origin_basename = Path(files[0]).stem

        # disable check for existing subset with the same name
        """
        asset = get_asset_by_name(
            self.project_name, instance_data["asset"], fields=["_id"])

        if get_subset_by_name(
                self.project_name, origin_basename, asset["_id"],
                fields=["_id"]):
            raise CreatorError(f"subset with {origin_basename} already "
                               "exists in selected asset")
        """

        instance_data["originalBasename"] = origin_basename
        subset_name = origin_basename

        instance_data["creator_attributes"] = {
            "path": (Path(repr_file["directory"]) / files[0]).as_posix()
        }

        # Create new instance
        new_instance = CreatedInstance(self.family, subset_name,
                                       instance_data, self)
        self._store_new_instance(new_instance)

    def get_instance_attr_defs(self):
        return [
            BoolDef(
                "add_review_family",
                default=True,
                label="Review"
            )
        ]

    def get_pre_create_attr_defs(self):
        return [
            FileDef(
                "representation_file",
                folders=False,
                extensions=self.extensions,
                allow_sequences=True,
                single_item=True,
                label="Representation",
            ),
            BoolDef(
                "add_review_family",
                default=True,
                label="Review"
            )
        ]

    def get_subset_name(
        self,
        variant,
        task_name,
        asset_doc,
        project_name,
        host_name=None,
        instance=None
    ):
        if instance is None:
            return "{originalBasename}"

        return instance.data["subset"]
