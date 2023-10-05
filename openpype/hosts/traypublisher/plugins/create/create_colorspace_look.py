# -*- coding: utf-8 -*-
"""Creator of colorspace look files.

This creator is used to publish colorspace look files thanks to
production type `ociolook`. All files are published as representation.
"""
from pathlib import Path

from openpype.client import get_asset_by_name
from openpype.lib.attribute_definitions import (
    FileDef, EnumDef, TextDef, UISeparatorDef
)
from openpype.pipeline import (
    CreatedInstance,
    CreatorError
)
from openpype.pipeline.create import (
    get_subset_name,
    TaskNotSetError,
)
from openpype.pipeline import colorspace
from openpype.hosts.traypublisher.api.plugin import TrayPublishCreator


class CreateColorspaceLook(TrayPublishCreator):
    """Creates colorspace look files."""

    identifier = "io.openpype.creators.traypublisher.colorspace_look"
    label = "Colorspace Look"
    family = "ociolook"
    description = "Publishes color space look file."
    extensions = [".cc", ".cube", ".3dl", ".spi1d", ".spi3d", ".csp", ".lut"]
    enabled = False

    colorspace_items = [
        (None, "Not set")
    ]
    colorspace_attr_show = False
    config_items = None

    def get_detail_description(self):
        return """# Colorspace Look

This creator publishes color space look file (LUT).
        """

    def get_icon(self):
        return "mdi.format-color-fill"

    def create(self, subset_name, instance_data, pre_create_data):
        repr_file = pre_create_data.get("luts_file")
        if not repr_file:
            raise CreatorError("No files specified")

        files = repr_file.get("filenames")
        if not files:
            # this should never happen
            raise CreatorError("Missing files from representation")

        asset_doc = get_asset_by_name(
            self.project_name, instance_data["asset"])

        subset_name = self._get_subset(
            asset_doc, instance_data["variant"], self.project_name,
            instance_data["task"]
        )

        instance_data["creator_attributes"] = {
            "abs_lut_path": (
                Path(repr_file["directory"]) / files[0]).as_posix()
        }

        # Create new instance
        new_instance = CreatedInstance(self.family, subset_name,
                                       instance_data, self)
        self._store_new_instance(new_instance)

    def get_instance_attr_defs(self):
        return [
            EnumDef(
                "working_colorspace",
                self.colorspace_items,
                default="Not set",
                label="Working Colorspace",
            ),
            UISeparatorDef(
                label="Advanced1"
            ),
            TextDef(
                "abs_lut_path",
                label="LUT Path",
            ),
            EnumDef(
                "input_colorspace",
                self.colorspace_items,
                default="Not set",
                label="Input Colorspace",
            ),
            EnumDef(
                "direction",
                [
                    (None, "Not set"),
                    ("forward", "Forward"),
                    ("inverse", "Inverse")
                ],
                default="Not set",
                label="Direction"
            ),
            EnumDef(
                "interpolation",
                [
                    (None, "Not set"),
                    ("linear", "Linear"),
                    ("tetrahedral", "Tetrahedral"),
                    ("best", "Best"),
                    ("nearest", "Nearest")
                ],
                default="Not set",
                label="Interpolation"
            ),
            EnumDef(
                "output_colorspace",
                self.colorspace_items,
                default="Not set",
                label="Output Colorspace",
            ),
        ]

    def get_pre_create_attr_defs(self):
        return [
            FileDef(
                "luts_file",
                folders=False,
                extensions=self.extensions,
                allow_sequences=False,
                single_item=True,
                label="Look Files",
            )
        ]

    def apply_settings(self, project_settings, system_settings):
        host = self.create_context.host
        host_name = host.name
        project_name = host.get_current_project_name()
        config_data = colorspace.get_imageio_config(
            project_name, host_name,
            project_settings=project_settings
        )

        if config_data:
            filepath = config_data["path"]
            config_items = colorspace.get_ocio_config_colorspaces(filepath)
            labeled_colorspaces = colorspace.get_colorspaces_enumerator_items(
                config_items,
                include_aliases=True,
                include_roles=True
            )
            self.config_items = config_items
            self.colorspace_items.extend(labeled_colorspaces)
            self.enabled = True

    def _get_subset(self, asset_doc, variant, project_name, task_name=None):
        """Create subset name according to standard template process"""

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

        return subset_name
