# -*- coding: utf-8 -*-
"""Validate settings from Deadline Submitter.

This is useful mainly for tile rendering, where jobs on farm are created by
submitter script from Maya.

Unfortunately Deadline doesn't expose frame number for tiles job so that
cannot be validated, even if it is important setting. Also we cannot
determine if 'Region Rendering' (tile rendering) is enabled or not because
of the same thing.

"""
import os

from maya import mel
from maya import cmds

import pyblish.api
from pype.hosts.maya import lib


class ValidateDeadlineTileSubmission(pyblish.api.InstancePlugin):
    """Validate Deadline Submission settings are OK for tile rendering."""

    label = "Validate Deadline Tile Submission"
    order = pyblish.api.ValidatorOrder
    hosts = ["maya"]
    families = ["renderlayer"]
    if not os.environ.get("DEADLINE_REST_URL"):
        active = False

    def process(self, instance):
        """Entry point."""
        # try if Deadline submitter was loaded
        if mel.eval("exists SubmitJobToDeadline") == 0:
            # if not, try to load it manually
            try:
                mel.eval("source DeadlineMayaClient;")
            except RuntimeError:
                raise AssertionError("Deadline Maya client cannot be loaded")
            mel.eval("DeadlineMayaClient();")
            assert mel.eval("exists SubmitJobToDeadline") == 1, (
                "Deadline Submission script cannot be initialized.")
        if instance.data.get("tileRendering"):
            job_name = cmds.getAttr("defaultRenderGlobals.deadlineJobName")
            scene_name = os.path.splitext(os.path.basename(
                instance.context.data.get("currentFile")))[0]
            if job_name != scene_name:
                self.log.warning(("Job submitted through Deadline submitter "
                                  "has different name then current scene "
                                  "{} / {}").format(job_name, scene_name))
            if cmds.getAttr("defaultRenderGlobals.deadlineTileSingleJob") == 1:
                layer = instance.data['setMembers']
                anim_override = lib.get_attr_in_layer(
                    "defaultRenderGlobals.animation", layer=layer)
                assert anim_override, (
                    "Animation must be enabled in "
                    "Render Settings even when rendering single frame."
                )

                start_frame = cmds.getAttr("defaultRenderGlobals.startFrame")
                end_frame = cmds.getAttr("defaultRenderGlobals.endFrame")
                assert start_frame == end_frame, (
                    "Start frame and end frame are not equals. When "
                    "'Submit All Tles As A Single Job' is selected, only "
                    "single frame is expected to be rendered. It must match "
                    "the one specified in Deadline Submitter under "
                    "'Region Rendering'"
                )
