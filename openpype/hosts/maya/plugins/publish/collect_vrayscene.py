# -*- coding: utf-8 -*-
"""Collect Vray Scene and prepare it for extraction and publishing."""
import re

import maya.app.renderSetup.model.renderSetup as renderSetup
from maya import cmds

import pyblish.api

from openpype.pipeline import legacy_io
from openpype.lib import get_formatted_current_time
from openpype.hosts.maya.api import lib


class CollectVrayScene(pyblish.api.InstancePlugin):
    """Collect Vray Scene.

    If export on farm is checked, job is created to export it.
    """

    order = pyblish.api.CollectorOrder + 0.01
    label = "Collect Vray Scene"
    families = ["vrayscene"]

    def process(self, instance):
        """Collector entry point."""

        context = instance.context

        layer = instance.data["transientData"]["layer"]
        layer_name = layer.name()

        renderer = self.get_render_attribute("currentRenderer",
                                             layer=layer_name)
        if renderer != "vray":
            self.log.warning("Layer '{}' renderer is not set to V-Ray".format(
                layer_name
            ))

        # collect all frames we are expecting to be rendered
        frame_start_render = int(self.get_render_attribute(
            "startFrame", layer=layer_name))
        frame_end_render = int(self.get_render_attribute(
            "endFrame", layer=layer_name))

        if (int(context.data['frameStartHandle']) == frame_start_render
                and int(context.data['frameEndHandle']) == frame_end_render):  # noqa: W503, E501

            handle_start = context.data['handleStart']
            handle_end = context.data['handleEnd']
            frame_start = context.data['frameStart']
            frame_end = context.data['frameEnd']
            frame_start_handle = context.data['frameStartHandle']
            frame_end_handle = context.data['frameEndHandle']
        else:
            handle_start = 0
            handle_end = 0
            frame_start = frame_start_render
            frame_end = frame_end_render
            frame_start_handle = frame_start_render
            frame_end_handle = frame_end_render

        # Get layer specific settings, might be overrides
        data = {
            "subset": layer_name,
            "layer": layer_name,
            # TODO: This likely needs fixing now
            # Before refactor: cmds.sets(layer, q=True) or ["*"]
            "setMembers": ["*"],
            "review": False,
            "publish": True,
            "handleStart": handle_start,
            "handleEnd": handle_end,
            "frameStart": frame_start,
            "frameEnd": frame_end,
            "frameStartHandle": frame_start_handle,
            "frameEndHandle": frame_end_handle,
            "byFrameStep": int(
                self.get_render_attribute("byFrameStep",
                                          layer=layer_name)),
            "renderer": renderer,
            # instance subset
            "family": "vrayscene_layer",
            "families": ["vrayscene_layer"],
            "time": get_formatted_current_time(),
            "author": context.data["user"],
            # Add source to allow tracing back to the scene from
            # which was submitted originally
            "source": context.data["currentFile"].replace("\\", "/"),
            "resolutionWidth": lib.get_attr_in_layer(
                "defaultResolution.height", layer=layer_name
            ),
            "resolutionHeight": lib.get_attr_in_layer(
                "defaultResolution.width", layer=layer_name
            ),
            "pixelAspect": lib.get_attr_in_layer(
                "defaultResolution.pixelAspect", layer=layer_name
            ),
            "priority": instance.data.get("priority"),
            "useMultipleSceneFiles": instance.data.get(
                "vraySceneMultipleFiles")
        }

        instance.data.update(data)

        # Define nice label
        label = "{0} ({1})".format(layer_name, instance.data["asset"])
        label += "  [{0}-{1}]".format(
            int(data["frameStartHandle"]), int(data["frameEndHandle"])
        )
        instance.data["label"] = label

    def get_render_attribute(self, attr, layer):
        """Get attribute from render options.

        Args:
            attr (str): name of attribute to be looked up.

        Returns:
            Attribute value

        """
        return lib.get_attr_in_layer(
            "defaultRenderGlobals.{}".format(attr), layer=layer
        )
