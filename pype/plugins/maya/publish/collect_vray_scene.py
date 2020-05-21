# -*- coding: utf-8 -*-
"""Collect .vrayscene instance."""
import os

import pyblish.api

from maya import cmds

from avalon import api
from pype.maya.expected_files import ExpectedFiles


class CollectVRayScene(pyblish.api.ContextPlugin):
    """Collect all information prior for exporting vrscenes."""

    order = pyblish.api.CollectorOrder
    label = "Collect VRay Scene"
    hosts = ["foo"]

    def process(self, context):
        """Collector entry point."""
        # Sort by displayOrder
        def sort_by_display_order(layer):
            return cmds.getAttr("%s.displayOrder" % layer)

        host = api.registered_host()

        asset = api.Session["AVALON_ASSET"]
        work_dir = context.data["workspaceDir"]

        # Get VRay Scene instance
        vray_scenes = host.lsattr("family", "vrayscene")
        if not vray_scenes:
            self.log.info("Skipping vrayScene collection, no "
                          "vrayscene instance found..")
            return

        assert len(vray_scenes) == 1, "Multiple vrayscene instances found!"
        vray_scene = vray_scenes[0]

        vrscene_data = host.read(vray_scene)

        assert cmds.ls("vraySettings", type="VRaySettingsNode"), (
            "VRay Settings node does not exists. "
            "Please ensure V-Ray is the current renderer."
        )

        # Output data
        start_frame = int(cmds.getAttr("defaultRenderGlobals.startFrame"))
        end_frame = int(cmds.getAttr("defaultRenderGlobals.endFrame"))

        # Create output file path with template
        file_name = context.data["currentFile"].replace("\\", "/")
        vrscene = ("vrayscene", "<Scene>", "<Scene>_<Layer>", "<Layer>")
        vrscene_output = os.path.join(work_dir, *vrscene)

        # Check and create render output template for render job
        # outputDir is required for submit_publish_job
        if not vrscene_data.get("suspendRenderJob", False):
            renders = ("renders", "<Scene>", "<Scene>_<Layer>", "<Layer>")
            output_renderpath = os.path.join(work_dir, *renders)
            vrscene_data["outputDir"] = output_renderpath

        # Get resolution
        resolution = (cmds.getAttr("defaultResolution.width"),
                      cmds.getAttr("defaultResolution.height"))

        # Get format extension
        extension = cmds.getAttr("vraySettings.imageFormatStr")

        # Get render layers
        render_layers = [i for i in cmds.ls(type="renderLayer") if
                         cmds.getAttr("{}.renderable".format(i)) and not
                         cmds.referenceQuery(i, isNodeReferenced=True)]

        render_layers = sorted(render_layers, key=sort_by_display_order)
        for layer in render_layers:

            subset = layer
            if subset == "defaultRenderLayer":
                subset = "masterLayer"

            data = {
                "subset": subset,
                "setMembers": layer,

                "frameStart": start_frame,
                "frameEnd": end_frame,
                "renderer": "vray",
                "resolution": resolution,
                "ext": ".{}".format(extension),

                # instance subset
                "family": "VRay Scene",
                "families": ["vrayscene"],
                "asset": asset,
                "time": api.time(),
                "author": context.data["user"],

                # Add source to allow tracing back to the scene from
                # which was submitted originally
                "source": file_name,

                # Store VRay Scene additional data
                "vrsceneOutput": vrscene_output
            }

            data.update(vrscene_data)

            instance = context.create_instance(subset)
            self.log.info("Created: %s" % instance.name)
            instance.data.update(data)
