# -*- coding: utf-8 -*-
"""Extract project for Maya"""

import contextlib
from pathlib import Path

import pyblish.api
import tde4

from openpype.lib import BoolDef, EnumDef, NumberDef, import_filepath
from openpype.pipeline import (
    KnownPublishError,
    OpenPypePyblishPluginMixin,
    publish,
)


@contextlib.contextmanager
def maintained_model_selection():
    """Maintain model selection during context."""

    # 1 get camera point_group
    point_group = None
    selected_models = []
    point_groups = tde4.getPGroupList()
    for pg in point_groups:
        if tde4.getPGroupType(point_group) == "CAMERA":
            point_group = pg
            break
    if point_group:
        # 2 get current model selection
        selected_models = tde4.get3DModelList(point_group, 1)
    try:
        yield
    finally:
        if point_group:
            # 3 restore model selection
            for model in tde4.get3DModelList(point_group, 0):
                if model in selected_models:
                    tde4.set3DModelSelectionFlag(point_group, model, 1)
                else:
                    tde4.set3DModelSelectionFlag(point_group, model, 0)


class ExtractMatchmoveScriptMaya(
    publish.Extractor, OpenPypePyblishPluginMixin):

    label = "Extract Maya Script"
    families = ["matchmove"]
    hosts = ["equalizer"]

    order = pyblish.api.ExtractorOrder

    hide_reference_frame = False
    export_uv_textures = False
    overscan_percent_width = 100
    overscan_percent_height = 100
    units = "mm"

    @classmethod
    def apply_settings(cls, project_settings, system_settings):
        settings = project_settings["equalizer"]["publish"]["ExtractMatchmoveScriptMaya"]  # noqa

        cls.hide_reference_frame = settings.get(
            "hide_reference_frame", cls.hide_reference_frame)
        cls.export_uv_textures = settings.get(
            "export_uv_textures", cls.export_uv_textures)
        cls.overscan_percent_width = settings.get(
            "overscan_percent_width", cls.overscan_percent_width)
        cls.overscan_percent_height = settings.get(
            "overscan_percent_height", cls.overscan_percent_height)
        cls.units = settings.get("units", cls.units)

    @classmethod
    def get_attribute_defs(cls):
        defs = super(ExtractMatchmoveScriptMaya, cls).get_attribute_defs()

        defs.extend([
            BoolDef("hide_reference_frame",
                      label="Hide Reference Frame",
                      default=cls.hide_reference_frame),
            BoolDef("export_uv_textures",
                    label="Export UV Textures",
                    default=cls.export_uv_textures),
            NumberDef("overscan_percent_width",
                      label="Overscan Width %",
                      default=cls.overscan_percent_width,
                      decimals=0,
                      minimum=1,
                      maximum=1000),
            NumberDef("overscan_percent_height",
                      label="Overscan Height %",
                      default=cls.overscan_percent_height,
                      decimals=0,
                      minimum=1,
                      maximum=1000),
            EnumDef("units",
                    ["mm", "cm", "m", "in", "ft", "yd"],
                    default=cls.units,
                    label="Units"),
        ])
        return defs

    def process(self, instance):
        attr_data = self.get_attr_values_from_data(instance.data)

        # import maya export script from 3dequalizer
        exporter_path = instance.data["tde4_path"] / "sys_data" / "py_scripts" / "export_maya.py"  # noqa: E501
        self.log.debug(f"Importing {exporter_path.as_posix()}")
        exporter = import_filepath(exporter_path)

        # get camera point group
        point_group = None
        point_groups = tde4.getPGroupList()
        for pg in point_groups:
            if tde4.getPGroupType(point_group) == "CAMERA":
                point_group = pg
                break
        else:
            # this should never happen as it should be handled by validator
            raise RuntimeError("No camera point group found.")

        offset = tde4.getCameraFrameOffset(tde4.getCurrentCamera())
        overscan_width = attr_data["overscan_percent_width"] / 100.0
        overscan_height = attr_data["overscan_percent_height"] / 100.0

        staging_dir = Path(self.staging_dir(instance))

        unit_scales = {
            "mm": 10.0,  # cm -> mm
            "cm": 1.0,  # cm -> cm
            "m": 0.01,  # cm -> m
            "in": 0.393701,  # cm -> in
            "ft": 0.0328084,  # cm -> ft
            "yd": 0.0109361  # cm -> yd
        }
        scale_factor = unit_scales[attr_data["units"]]

        with maintained_model_selection():
            # handle model selection
            # We are passing it to existing function that is expecting
            # this value to be an index of selection type.
            # 1 - No models
            # 2 - Selected models
            # 3 - All models
            if instance.data["model_selection"] == "__none__":
                model_selection = 1
            elif instance.data["model_selection"] == "__all__":
                model_selection = 3
            else:
                # take model from instance and set its selection flag on
                # turn off all others
                model_selection = 2
                point_groups = tde4.getPGroupList()
                for point_group in point_groups:
                    model_list = tde4.get3DModelList(point_group, 0)
                    if instance.data["model_selection"] in model_list:
                        model_selection = 2
                        tde4.set3DModelSelectionFlag(
                            point_group, instance.data["model_selection"], 1)
                        break
                    else:
                        # clear all other model selections
                        for model in model_list:
                            tde4.set3DModelSelectionFlag(point_group, model, 0)

            status = exporter._maya_export_mel_file(
                (staging_dir / "maya_export.mel").as_posix(),  # staging path
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
