# -*- coding: utf-8 -*-
"""Fbx Extractor for houdini. """

import os
import pyblish.api
from openpype.pipeline import publish
from openpype.hosts.houdini.api.lib import render_rop

import hou


class ExtractFBX(publish.Extractor):

    label = "Extract FBX"
    families = ["fbx"]
    hosts = ["houdini"]

    order = pyblish.api.ExtractorOrder + 0.1

    def process(self, instance):

        # get rop node
        ropnode = hou.node(instance.data.get("instance_node"))
        output_file = ropnode.evalParm("sopoutput")

        # get staging_dir and file_name
        staging_dir = os.path.normpath(os.path.dirname(output_file))
        file_name = os.path.basename(output_file)

        # render rop
        self.log.debug("Writing FBX '%s' to '%s'", file_name, staging_dir)
        render_rop(ropnode)

        # prepare representation
        representation = {
            "name": "fbx",
            "ext": "fbx",
            "files": file_name,
            "stagingDir": staging_dir
        }

        # A single frame may also be rendered without start/end frame.
        if "frameStartHandle" in instance.data and "frameEndHandle" in instance.data:  # noqa
            representation["frameStart"] = instance.data["frameStartHandle"]
            representation["frameEnd"] = instance.data["frameEndHandle"]

        # set value type for 'representations' key to list
        if "representations" not in instance.data:
            instance.data["representations"] = []

        # update instance data
        instance.data["stagingDir"] = staging_dir
        instance.data["representations"].append(representation)
