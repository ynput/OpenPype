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
        collected_render_layers = instance.data["setMembers"]
        instance.data["remove"] = True
        context = instance.context

        _rs = renderSetup.instance()
        # current_layer = _rs.getVisibleRenderLayer()

        # collect all frames we are expecting to be rendered
        renderer = cmds.getAttr(
            "defaultRenderGlobals.currentRenderer"
        ).lower()

        if renderer != "vray":
            raise AssertionError("Vray is not enabled.")

        maya_render_layers = {
            layer.name(): layer for layer in _rs.getRenderLayers()
        }

        layer_list = []
        for layer in collected_render_layers:
            # every layer in set should start with `LAYER_` prefix
            try:
                expected_layer_name = re.search(r"^.+:(.*)", layer).group(1)
            except IndexError:
                msg = "Invalid layer name in set [ {} ]".format(layer)
                self.log.warning(msg)
                continue

            self.log.info("processing %s" % layer)
            # check if layer is part of renderSetup
            if expected_layer_name not in maya_render_layers:
                msg = "Render layer [ {} ] is not in " "Render Setup".format(
                    expected_layer_name
                )
                self.log.warning(msg)
                continue

            # check if layer is renderable
            if not maya_render_layers[expected_layer_name].isRenderable():
                msg = "Render layer [ {} ] is not " "renderable".format(
                    expected_layer_name
                )
                self.log.warning(msg)
                continue

            layer_name = "rs_{}".format(expected_layer_name)

            self.log.debug(expected_layer_name)
            layer_list.append(expected_layer_name)

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
                "subset": expected_layer_name,
                "layer": layer_name,
                "setMembers": cmds.sets(layer, q=True) or ["*"],
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
                "renderer": self.get_render_attribute("currentRenderer",
                                                      layer=layer_name),
                # instance subset
                "family": "vrayscene_layer",
                "families": ["vrayscene_layer"],
                "asset": legacy_io.Session["AVALON_ASSET"],
                "time": get_formatted_current_time(),
                "author": context.data["user"],
                # Add source to allow tracing back to the scene from
                # which was submitted originally
                "source": context.data["currentFile"].replace("\\", "/"),
                "resolutionWidth": cmds.getAttr("defaultResolution.width"),
                "resolutionHeight": cmds.getAttr("defaultResolution.height"),
                "pixelAspect": cmds.getAttr("defaultResolution.pixelAspect"),
                "priority": instance.data.get("priority"),
                "useMultipleSceneFiles": instance.data.get(
                    "vraySceneMultipleFiles")
            }

            # Define nice label
            label = "{0} ({1})".format(expected_layer_name, data["asset"])
            label += "  [{0}-{1}]".format(
                int(data["frameStartHandle"]), int(data["frameEndHandle"])
            )

            instance = context.create_instance(expected_layer_name)
            instance.data["label"] = label
            instance.data.update(data)

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
