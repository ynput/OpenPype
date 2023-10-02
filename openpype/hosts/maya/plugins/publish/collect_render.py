# -*- coding: utf-8 -*-
"""Collect render data.

This collector will go through render layers in maya and prepare all data
needed to create instances and their representations for submission and
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

import os
import platform
import json

from maya import cmds

import pyblish.api

from openpype.pipeline import KnownPublishError
from openpype.lib import get_formatted_current_time
from openpype.hosts.maya.api.lib_renderproducts import (
    get as get_layer_render_products,
    UnsupportedRendererException
)
from openpype.hosts.maya.api import lib


class CollectMayaRender(pyblish.api.InstancePlugin):
    """Gather all publishable render layers from renderSetup."""

    order = pyblish.api.CollectorOrder + 0.01
    hosts = ["maya"]
    families = ["renderlayer"]
    label = "Collect Render Layers"
    sync_workfile_version = False

    _aov_chars = {
        "dot": ".",
        "dash": "-",
        "underscore": "_"
    }

    def process(self, instance):

        # TODO: Re-add force enable of workfile instance?
        # TODO: Re-add legacy layer support with LAYER_ prefix but in Creator
        # TODO: Set and collect active state of RenderLayer in Creator using
        #       renderlayer.isRenderable()
        context = instance.context

        layer = instance.data["transientData"]["layer"]
        objset = instance.data.get("instance_node")
        filepath = context.data["currentFile"].replace("\\", "/")
        workspace = context.data["workspaceDir"]

        # check if layer is renderable
        if not layer.isRenderable():
            msg = "Render layer [ {} ] is not " "renderable".format(
                layer.name()
            )
            self.log.warning(msg)

        # detect if there are sets (subsets) to attach render to
        sets = cmds.sets(objset, query=True) or []
        attach_to = []
        for s in sets:
            if not cmds.attributeQuery("family", node=s, exists=True):
                continue

            attach_to.append(
                {
                    "version": None,  # we need integrator for that
                    "subset": s,
                    "family": cmds.getAttr("{}.family".format(s)),
                }
            )
            self.log.debug(" -> attach render to: {}".format(s))

        layer_name = layer.name()

        # collect all frames we are expecting to be rendered
        # return all expected files for all cameras and aovs in given
        # frame range
        try:
            layer_render_products = get_layer_render_products(layer.name())
        except UnsupportedRendererException as exc:
            raise KnownPublishError(exc)
        render_products = layer_render_products.layer_data.products
        assert render_products, "no render products generated"
        expected_files = []
        multipart = False
        for product in render_products:
            if product.multipart:
                multipart = True
            product_name = product.productName
            if product.camera and layer_render_products.has_camera_token():
                product_name = "{}{}".format(
                    product.camera,
                    "_{}".format(product_name) if product_name else "")
            expected_files.append(
                {
                    product_name: layer_render_products.get_files(
                        product)
                })

        has_cameras = any(product.camera for product in render_products)
        assert has_cameras, "No render cameras found."

        self.log.debug("multipart: {}".format(
            multipart))
        assert expected_files, "no file names were generated, this is a bug"
        self.log.debug(
            "expected files: {}".format(
                json.dumps(expected_files, indent=4, sort_keys=True)
            )
        )

        # if we want to attach render to subset, check if we have AOV's
        # in expectedFiles. If so, raise error as we cannot attach AOV
        # (considered to be subset on its own) to another subset
        if attach_to:
            assert isinstance(expected_files, list), (
                "attaching multiple AOVs or renderable cameras to "
                "subset is not supported"
            )

        # append full path
        aov_dict = {}
        image_directory = os.path.join(
            cmds.workspace(query=True, rootDirectory=True),
            cmds.workspace(fileRuleEntry="images")
        )
        # replace relative paths with absolute. Render products are
        # returned as list of dictionaries.
        publish_meta_path = None
        for aov in expected_files:
            full_paths = []
            aov_first_key = list(aov.keys())[0]
            for file in aov[aov_first_key]:
                full_path = os.path.join(image_directory, file)
                full_path = full_path.replace("\\", "/")
                full_paths.append(full_path)
                publish_meta_path = os.path.dirname(full_path)
            aov_dict[aov_first_key] = full_paths
        full_exp_files = [aov_dict]
        self.log.debug(full_exp_files)

        if publish_meta_path is None:
            raise KnownPublishError("Unable to detect any expected output "
                                    "images for: {}. Make sure you have a "
                                    "renderable camera and a valid frame "
                                    "range set for your renderlayer."
                                    "".format(instance.name))

        frame_start_render = int(self.get_render_attribute(
            "startFrame", layer=layer_name))
        frame_end_render = int(self.get_render_attribute(
            "endFrame", layer=layer_name))

        if (int(context.data["frameStartHandle"]) == frame_start_render
                and int(context.data["frameEndHandle"]) == frame_end_render):  # noqa: W503, E501

            handle_start = context.data["handleStart"]
            handle_end = context.data["handleEnd"]
            frame_start = context.data["frameStart"]
            frame_end = context.data["frameEnd"]
            frame_start_handle = context.data["frameStartHandle"]
            frame_end_handle = context.data["frameEndHandle"]
        else:
            handle_start = 0
            handle_end = 0
            frame_start = frame_start_render
            frame_end = frame_end_render
            frame_start_handle = frame_start_render
            frame_end_handle = frame_end_render

        # find common path to store metadata
        # so if image prefix is branching to many directories
        # metadata file will be located in top-most common
        # directory.
        # TODO: use `os.path.commonpath()` after switch to Python 3
        publish_meta_path = os.path.normpath(publish_meta_path)
        common_publish_meta_path = os.path.splitdrive(
            publish_meta_path)[0]
        if common_publish_meta_path:
            common_publish_meta_path += os.path.sep
        for part in publish_meta_path.replace(
                common_publish_meta_path, "").split(os.path.sep):
            common_publish_meta_path = os.path.join(
                common_publish_meta_path, part)
            if part == layer_name:
                break

        # TODO: replace this terrible linux hotfix with real solution :)
        if platform.system().lower() in ["linux", "darwin"]:
            common_publish_meta_path = "/" + common_publish_meta_path

        self.log.debug(
            "Publish meta path: {}".format(common_publish_meta_path))

        # Get layer specific settings, might be overrides
        colorspace_data = lib.get_color_management_preferences()
        data = {
            "farm": True,
            "attachTo": attach_to,

            "multipartExr": multipart,
            "review": instance.data.get("review") or False,

            # Frame range
            "handleStart": handle_start,
            "handleEnd": handle_end,
            "frameStart": frame_start,
            "frameEnd": frame_end,
            "frameStartHandle": frame_start_handle,
            "frameEndHandle": frame_end_handle,
            "byFrameStep": int(
                self.get_render_attribute("byFrameStep",
                                          layer=layer_name)),

            # Renderlayer
            "renderer": self.get_render_attribute(
                "currentRenderer", layer=layer_name).lower(),
            "setMembers": layer._getLegacyNodeName(),  # legacy renderlayer
            "renderlayer": layer_name,

            # todo: is `time` and `author` still needed?
            "time": get_formatted_current_time(),
            "author": context.data["user"],

            # Add source to allow tracing back to the scene from
            # which was submitted originally
            "source": filepath,
            "expectedFiles": full_exp_files,
            "publishRenderMetadataFolder": common_publish_meta_path,
            "renderProducts": layer_render_products,
            "resolutionWidth": lib.get_attr_in_layer(
                "defaultResolution.width", layer=layer_name
            ),
            "resolutionHeight": lib.get_attr_in_layer(
                "defaultResolution.height", layer=layer_name
            ),
            "pixelAspect": lib.get_attr_in_layer(
                "defaultResolution.pixelAspect", layer=layer_name
            ),

            # todo: Following are likely not needed due to collecting from the
            #       instance itself if they are attribute definitions
            "tileRendering": instance.data.get("tileRendering") or False,  # noqa: E501
            "tilesX": instance.data.get("tilesX") or 2,
            "tilesY": instance.data.get("tilesY") or 2,
            "convertToScanline": instance.data.get(
                "convertToScanline") or False,
            "useReferencedAovs": instance.data.get(
                "useReferencedAovs") or instance.data.get(
                    "vrayUseReferencedAovs") or False,
            "aovSeparator": layer_render_products.layer_data.aov_separator,  # noqa: E501
            "renderSetupIncludeLights": instance.data.get(
                "renderSetupIncludeLights"
            ),
            "colorspaceConfig": colorspace_data["config"],
            "colorspaceDisplay": colorspace_data["display"],
            "colorspaceView": colorspace_data["view"],
        }

        rr_settings = (
            context.data["system_settings"]["modules"]["royalrender"]
        )
        if rr_settings["enabled"]:
            data["rrPathName"] = instance.data.get("rrPathName")
            self.log.debug(data["rrPathName"])

        if self.sync_workfile_version:
            data["version"] = context.data["version"]
            for _instance in context:
                if _instance.data['family'] == "workfile":
                    _instance.data["version"] = context.data["version"]

        # Define nice label
        label = "{0} ({1})".format(layer_name, instance.data["asset"])
        label += "  [{0}-{1}]".format(
            int(data["frameStartHandle"]), int(data["frameEndHandle"])
        )
        data["label"] = label

        # Override frames should be False if extendFrames is False. This is
        # to ensure it doesn't go off doing crazy unpredictable things
        extend_frames = instance.data.get("extendFrames", False)
        if not extend_frames:
            instance.data["overrideExistingFrame"] = False

        # Update the instace
        instance.data.update(data)

    @staticmethod
    def get_render_attribute(attr, layer):
        """Get attribute from render options.

        Args:
            attr (str): name of attribute to be looked up
            layer (str): name of render layer

        Returns:
            Attribute value

        """
        return lib.get_attr_in_layer(
            "defaultRenderGlobals.{}".format(attr), layer=layer
        )
