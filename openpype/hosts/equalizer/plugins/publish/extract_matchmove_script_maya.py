# -*- coding: utf-8 -*-
"""Extract project for Maya"""

from pathlib import Path

import pyblish.api
import tde4

from openpype.hosts.equalizer.api import (
    ExtractScriptBase,
    maintained_model_selection,
)
from openpype.lib import import_filepath
from openpype.pipeline import (
    KnownPublishError,
    OptionalPyblishPluginMixin,
    publish,
)


class ExtractMatchmoveScriptMaya(publish.Extractor,
                                 ExtractScriptBase,
                                 OptionalPyblishPluginMixin):
    """Extract Maya MEL script for matchmove.

    This is using built-in export script from 3DEqualizer.
    """

    label = "Extract Maya Script"
    families = ["matchmove"]
    hosts = ["equalizer"]

    order = pyblish.api.ExtractorOrder

    def process(self, instance: pyblish.api.Instance):
        """Extracts Maya script from 3DEqualizer.

        This method is using export script shipped with 3DEqualizer to
        maintain as much compatibility as possible. Instead of invoking it
        from the UI, it calls directly the function that is doing the export.
        For that it needs to pass some data that are collected in 3dequalizer
        from the UI, so we need to determine them from the instance itself and
        from the state of the project.

        """
        if not self.is_active(instance.data):
            return
        attr_data = self.get_attr_values_from_data(instance.data)

        # import maya export script from 3DEqualizer
        exporter_path = instance.data["tde4_path"] / "sys_data" / "py_scripts" / "export_maya.py"  # noqa: E501
        self.log.debug(f"Importing {exporter_path.as_posix()}")
        exporter = import_filepath(exporter_path.as_posix())

        # get camera point group
        point_group = None
        point_groups = tde4.getPGroupList()
        for pg in point_groups:
            if tde4.getPGroupType(pg) == "CAMERA":
                point_group = pg
                break
        else:
            # this should never happen as it should be handled by validator
            raise RuntimeError("No camera point group found.")

        offset = tde4.getCameraFrameOffset(tde4.getCurrentCamera())
        overscan_width = attr_data["overscan_percent_width"] / 100.0
        overscan_height = attr_data["overscan_percent_height"] / 100.0

        staging_dir = self.staging_dir(instance)

        unit_scales = {
            "mm": 10.0,  # cm -> mm
            "cm": 1.0,  # cm -> cm
            "m": 0.01,  # cm -> m
            "in": 0.393701,  # cm -> in
            "ft": 0.0328084,  # cm -> ft
            "yd": 0.0109361  # cm -> yd
        }
        scale_factor = unit_scales[attr_data["units"]]
        model_selection_enum = instance.data["creator_attributes"]["model_selection"]  # noqa: E501

        with maintained_model_selection():
            # handle model selection
            # We are passing it to existing function that is expecting
            # this value to be an index of selection type.
            # 1 - No models
            # 2 - Selected models
            # 3 - All models
            if model_selection_enum == "__none__":
                model_selection = 1
            elif model_selection_enum == "__all__":
                model_selection = 3
            else:
                # take model from instance and set its selection flag on
                # turn off all others
                model_selection = 2
                point_groups = tde4.getPGroupList()
                for point_group in point_groups:
                    model_list = tde4.get3DModelList(point_group, 0)
                    if model_selection_enum in model_list:
                        model_selection = 2
                        tde4.set3DModelSelectionFlag(
                            point_group, instance.data["model_selection"], 1)
                        break
                    else:
                        # clear all other model selections
                        for model in model_list:
                            tde4.set3DModelSelectionFlag(point_group, model, 0)

            file_path = Path(staging_dir) / "maya_export.mel"
            status = exporter._maya_export_mel_file(
                file_path.as_posix(),  # staging path
                point_group,  # camera point group
                [c["id"] for c in instance.data["cameras"] if c["enabled"]],
                model_selection,  # model selection mode
                overscan_width,
                overscan_height,
                1 if attr_data["export_uv_textures"] else 0,
                scale_factor,
                offset,  # start frame
                1 if attr_data["hide_reference_frame"] else 0)

        if status != 1:
            raise KnownPublishError("Export failed.")

        # create representation data
        if "representations" not in instance.data:
            instance.data["representations"] = []

        representation = {
            'name': "mel",
            'ext': "mel",
            'files': file_path.name,
            "stagingDir": staging_dir,
        }
        self.log.debug(f"output: {file_path.as_posix()}")
        instance.data["representations"].append(representation)
