import os

import pyblish.api

from avalon import api, maya

from maya import cmds


class CollectVRayScene(pyblish.api.ContextPlugin):

    order = pyblish.api.CollectorOrder
    label = "Collect VRay Scene"
    hosts = ["maya"]

    def process(self, context):

        asset = api.Session["AVALON_ASSET"]

        AVALON_DEADLINE = api.Session.get("AVALON_DEADLINE", None)
        assert AVALON_DEADLINE, "Can't submit without Deadline connection!"

        context.data["deadlineUrl"] = "{}/api/jobs".format(AVALON_DEADLINE)

        # Create output file path with template
        file_name = context.data["currentFile"].replace("\\", "/")
        output_filepath = os.path.join(context.data["workspaceDir"],
                                       "vrayscene",
                                       "<Scene>",
                                       "<Layer>",
                                       "<Scene>_<Layer>")

        context.data["outputFilePath"] = output_filepath

        # Get VRay Scene instance
        vray_scenes = maya.lsattr("family", "colorbleed.vrayscene")
        if not vray_scenes:
            self.log.info("No instance found of family: `colorbleed.vrayscene`")
            return

        assert len(vray_scenes) == 1, "Multiple vrayscene instances found!"
        vray_scene = vray_scenes[0]

        camera = cmds.getAttr("{}.camera".format(vray_scene)) or "persp"

        # Animation data
        start_frame = cmds.getAttr("defaultRenderGlobals.startFrame")
        end_frame = cmds.getAttr("defaultRenderGlobals.endFrame")
        context.data["startFrame"] = int(start_frame)
        context.data["endFrame"] = int(end_frame)

        # Get render layers
        renderlayers = [i for i in cmds.ls(type="renderLayer") if
                        cmds.getAttr("{}.renderable".format(i)) and not
                        cmds.referenceQuery(i, isNodeReferenced=True)]

        # Sort by displayOrder
        def sort_by_display_order(layer):
            return cmds.getAttr("%s.displayOrder" % layer)

        renderlayers = sorted(renderlayers, key=sort_by_display_order)

        resolution = (cmds.getAttr("defaultResolution.width"),
                      cmds.getAttr("defaultResolution.height"))

        for layer in renderlayers:

            if layer.endswith("defaultRenderLayer"):
                layer = "masterLayer"

            data = {
                "subset": layer,
                "setMembers": layer,

                "camera": camera,
                "startFrame": start_frame,
                "endFrame": end_frame,
                "renderer": "vray",
                "resolution": resolution,

                # instance subset
                "family": "VRay Scene",
                "families": ["colorbleed.vrayscene"],
                "asset": asset,
                "time": api.time(),
                "author": context.data["user"],

                # Add source to allow tracing back to the scene from
                # which was submitted originally
                "source": file_name
            }

            instance = context.create_instance(layer)
            self.log.info("Created: %s" % instance.name)
            instance.data.update(data)
