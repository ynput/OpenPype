# -*- coding: utf-8 -*-
"""Collect render data.

This collector will go through render layers in maya and prepare all data
needed to create instances and their representations for submition and
publishing on farm.

Requires:
    instance    -> families
    instance    -> setMembers

    context     -> currentFile
    context     -> workspaceDir
    context     -> user

    session     -> AVALON_ASSET

Optional:

Provides:
    instance    -> label
    instance    -> subset
    instance    -> attachTo
    instance    -> setMembers
    instance    -> publish
    instance    -> frameStart
    instance    -> frameEnd
    instance    -> byFrameStep
    instance    -> renderer
    instance    -> family
    instance    -> families
    instance    -> asset
    instance    -> time
    instance    -> author
    instance    -> source
    instance    -> expectedFiles
    instance    -> resolutionWidth
    instance    -> resolutionHeight
    instance    -> pixelAspect
"""

import re
import os
import json

from maya import cmds
import maya.app.renderSetup.model.renderSetup as renderSetup

import pyblish.api

from avalon import maya, api
from pype.hosts.maya.expected_files import ExpectedFiles
from pype.hosts.maya import lib


class CollectMayaRender(pyblish.api.ContextPlugin):
    """Gather all publishable render layers from renderSetup."""

    order = pyblish.api.CollectorOrder + 0.01
    hosts = ["maya"]
    label = "Collect Render Layers"

    def process(self, context):
        """Entry point to collector."""
        render_instance = None
        for instance in context:
            if "rendering" in instance.data["families"]:
                render_instance = instance
                render_instance.data["remove"] = True

            # make sure workfile instance publishing is enabled
            if "workfile" in instance.data["families"]:
                instance.data["publish"] = True

        if not render_instance:
            self.log.info(
                "No render instance found, skipping render "
                "layer collection."
            )
            return

        render_globals = render_instance
        collected_render_layers = render_instance.data["setMembers"]
        filepath = context.data["currentFile"].replace("\\", "/")
        asset = api.Session["AVALON_ASSET"]
        workspace = context.data["workspaceDir"]

        self._rs = renderSetup.instance()
        current_layer = self._rs.getVisibleRenderLayer()
        maya_render_layers = {
            layer.name(): layer for layer in self._rs.getRenderLayers()
        }

        self.maya_layers = maya_render_layers

        for layer in collected_render_layers:
            # every layer in set should start with `LAYER_` prefix
            try:
                expected_layer_name = re.search(r"^LAYER_(.*)", layer).group(1)
            except IndexError:
                msg = "Invalid layer name in set [ {} ]".format(layer)
                self.log.warnig(msg)
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

            # test if there are sets (subsets) to attach render to
            sets = cmds.sets(layer, query=True) or []
            attach_to = []
            if sets:
                for s in sets:
                    if "family" not in cmds.listAttr(s):
                        continue

                    attach_to.append(
                        {
                            "version": None,  # we need integrator for that
                            "subset": s,
                            "family": cmds.getAttr("{}.family".format(s)),
                        }
                    )
                    self.log.info(" -> attach render to: {}".format(s))

            layer_name = "rs_{}".format(expected_layer_name)

            # collect all frames we are expecting to be rendered
            renderer = cmds.getAttr(
                "defaultRenderGlobals.currentRenderer"
            ).lower()
            # handle various renderman names
            if renderer.startswith("renderman"):
                renderer = "renderman"

            # return all expected files for all cameras and aovs in given
            # frame range
            ef = ExpectedFiles()
            exp_files = ef.get(renderer, layer_name)
            self.log.info("multipart: {}".format(ef.multipart))
            assert exp_files, "no file names were generated, this is bug"

            # if we want to attach render to subset, check if we have AOV's
            # in expectedFiles. If so, raise error as we cannot attach AOV
            # (considered to be subset on its own) to another subset
            if attach_to:
                assert isinstance(exp_files, list), (
                    "attaching multiple AOVs or renderable cameras to "
                    "subset is not supported"
                )

            # append full path
            full_exp_files = []
            aov_dict = {}

            # we either get AOVs or just list of files. List of files can
            # mean two things - there are no AOVs enabled or multipass EXR
            # is produced. In either case we treat those as `beauty`.
            if isinstance(exp_files[0], dict):
                for aov, files in exp_files[0].items():
                    full_paths = []
                    for e in files:
                        full_path = os.path.join(workspace, "renders", e)
                        full_path = full_path.replace("\\", "/")
                        full_paths.append(full_path)
                    aov_dict[aov] = full_paths
            else:
                full_paths = []
                for e in exp_files:
                    full_path = os.path.join(workspace, "renders", e)
                    full_path = full_path.replace("\\", "/")
                    full_paths.append(full_path)
                aov_dict["beauty"] = full_paths

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

            full_exp_files.append(aov_dict)
            self.log.info(full_exp_files)
            self.log.info("collecting layer: {}".format(layer_name))
            # Get layer specific settings, might be overrides
            data = {
                "subset": expected_layer_name,
                "attachTo": attach_to,
                "setMembers": layer_name,
                "multipartExr": ef.multipart,
                "review": render_instance.data.get("review") or False,
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
                "family": "renderlayer",
                "families": ["renderlayer"],
                "asset": asset,
                "time": api.time(),
                "author": context.data["user"],
                # Add source to allow tracing back to the scene from
                # which was submitted originally
                "source": filepath,
                "expectedFiles": full_exp_files,
                "resolutionWidth": cmds.getAttr("defaultResolution.width"),
                "resolutionHeight": cmds.getAttr("defaultResolution.height"),
                "pixelAspect": cmds.getAttr("defaultResolution.pixelAspect"),
                "tileRendering": render_instance.data.get("tileRendering") or False,  # noqa: E501
                "tilesX": render_instance.data.get("tilesX") or 2,
                "tilesY": render_instance.data.get("tilesY") or 2,
                "priority": render_instance.data.get("priority")
            }

            # Apply each user defined attribute as data
            for attr in cmds.listAttr(layer, userDefined=True) or list():
                try:
                    value = cmds.getAttr("{}.{}".format(layer, attr))
                except Exception:
                    # Some attributes cannot be read directly,
                    # such as mesh and color attributes. These
                    # are considered non-essential to this
                    # particular publishing pipeline.
                    value = None

                data[attr] = value

            # handle standalone renderers
            if render_instance.data.get("vrayScene") is True:
                data["families"].append("vrayscene")

            if render_instance.data.get("assScene") is True:
                data["families"].append("assscene")

            # Include (optional) global settings
            # Get global overrides and translate to Deadline values
            overrides = self.parse_options(str(render_globals))
            data.update(**overrides)

            # Define nice label
            label = "{0} ({1})".format(expected_layer_name, data["asset"])
            label += "  [{0}-{1}]".format(
                int(data["frameStartHandle"]), int(data["frameEndHandle"])
            )

            instance = context.create_instance(expected_layer_name)
            instance.data["label"] = label
            instance.data.update(data)
            self.log.debug("data: {}".format(json.dumps(data, indent=4)))

        # Restore current layer.
        self.log.info("Restoring to {}".format(current_layer.name()))
        self._rs.switchToLayer(current_layer)

    def parse_options(self, render_globals):
        """Get all overrides with a value, skip those without.

        Here's the kicker. These globals override defaults in the submission
        integrator, but an empty value means no overriding is made.
        Otherwise, Frames would override the default frames set under globals.

        Args:
            render_globals (str): collection of render globals

        Returns:
            dict: only overrides with values

        """
        attributes = maya.read(render_globals)

        options = {"renderGlobals": {}}
        options["renderGlobals"]["Priority"] = attributes["priority"]

        # Check for specific pools
        pool_a, pool_b = self._discover_pools(attributes)
        options["renderGlobals"].update({"Pool": pool_a})
        if pool_b:
            options["renderGlobals"].update({"SecondaryPool": pool_b})

        # Machine list
        machine_list = attributes["machineList"]
        if machine_list:
            key = "Whitelist" if attributes["whitelist"] else "Blacklist"
            options["renderGlobals"][key] = machine_list

        # Suspend publish job
        state = "Suspended" if attributes["suspendPublishJob"] else "Active"
        options["publishJobState"] = state

        chunksize = attributes.get("framesPerTask", 1)
        options["renderGlobals"]["ChunkSize"] = chunksize

        # Override frames should be False if extendFrames is False. This is
        # to ensure it doesn't go off doing crazy unpredictable things
        override_frames = False
        extend_frames = attributes.get("extendFrames", False)
        if extend_frames:
            override_frames = attributes.get("overrideExistingFrame", False)

        options["extendFrames"] = extend_frames
        options["overrideExistingFrame"] = override_frames

        maya_render_plugin = "MayaPype"
        if attributes.get("useMayaBatch", True):
            maya_render_plugin = "MayaBatch"

        options["mayaRenderPlugin"] = maya_render_plugin

        return options

    def _discover_pools(self, attributes):

        pool_a = None
        pool_b = None

        # Check for specific pools
        pool_b = []
        if "primaryPool" in attributes:
            pool_a = attributes["primaryPool"]
            if "secondaryPool" in attributes:
                pool_b = attributes["secondaryPool"]

        else:
            # Backwards compatibility
            pool_str = attributes.get("pools", None)
            if pool_str:
                pool_a, pool_b = pool_str.split(";")

        # Ensure empty entry token is caught
        if pool_b == "-":
            pool_b = None

        return pool_a, pool_b

    def _get_overrides(self, layer):
        rset = self.maya_layers[layer].renderSettingsCollectionInstance()
        return rset.getOverrides()

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
