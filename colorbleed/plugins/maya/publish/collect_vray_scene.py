import os

import pyblish.api

from avalon import api, maya

from maya import cmds


class CollectVRayScene(pyblish.api.ContextPlugin):
    """Collect all information prior for exporting vrscenes
    """

    order = pyblish.api.CollectorOrder
    label = "Collect VRay Scene"
    hosts = ["maya"]

    def process(self, context):

        # Sort by displayOrder
        def sort_by_display_order(layer):
            return cmds.getAttr("%s.displayOrder" % layer)

        asset = api.Session["AVALON_ASSET"]
        work_dir = context.data["workspaceDir"]

        # Get VRay Scene instance
        vray_scenes = maya.lsattr("family", "colorbleed.vrayscene")
        if not vray_scenes:
            self.log.info("No instance found of family: `colorbleed.vrayscene`")
            return

        assert len(vray_scenes) == 1, "Multiple vrayscene instances found!"
        vray_scene = vray_scenes[0]

        vrscene_data = {k: cmds.getAttr("%s.%s" % (vray_scene, k)) for
                        k in cmds.listAttr(vray_scene, userDefined=True)}

        # Output data
        start_frame = int(cmds.getAttr("defaultRenderGlobals.startFrame"))
        end_frame = int(cmds.getAttr("defaultRenderGlobals.endFrame"))

        # Create output file path with template
        file_name = context.data["currentFile"].replace("\\", "/")
        vrscene = ("vrayscene", "<Scene>", "<Scene>_<Layer>", "<Layer>")
        vrscene_output = os.path.join(work_dir, *vrscene)

        vrscene_data["startFrame"] = start_frame
        vrscene_data["endFrame"] = end_frame
        vrscene_data["vrsceneOutput"] = vrscene_output

        context.data["startFrame"] = start_frame
        context.data["endFrame"] = end_frame

        # Check and create render output template for render job
        # outputDir is required for submit_publish_job
        if not vrscene_data.get("suspendRenderJob", False):
            renders = ("renders", "<Scene>", "<Scene>_<Layer>", "<Layer>")
            output_renderpath = os.path.join(work_dir, *renders)
            vrscene_data["outputDir"] = output_renderpath

        # Get resolution
        resolution = (cmds.getAttr("defaultResolution.width"),
                      cmds.getAttr("defaultResolution.height"))

        # Get render layers
        render_layers = [i for i in cmds.ls(type="renderLayer") if
                         cmds.getAttr("{}.renderable".format(i)) and not
                         cmds.referenceQuery(i, isNodeReferenced=True)]

        # Check if we need to filter out the default render layer
        if vrscene_data.get("includeDefaultRenderLayer", True):
            render_layers = [r for r in render_layers
                             if r != "defaultRenderLayer"]

        render_layers = sorted(render_layers, key=sort_by_display_order)
        for layer in render_layers:

            if layer.endswith("defaultRenderLayer"):
                layer = "masterLayer"

            data = {
                "subset": layer,
                "setMembers": layer,

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

            data.update(vrscene_data)

            instance = context.create_instance(layer)
            self.log.info("Created: %s" % instance.name)
            instance.data.update(data)
