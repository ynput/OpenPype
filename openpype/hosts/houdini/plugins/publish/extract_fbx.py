"""Extract FilmBox FBX.

Extractors are used to generate output and
update representation dictionary.

This plugin is part of publish process guide.
"""

import os

import pyblish.api

from openpype.pipeline import publish
from openpype.hosts.houdini.api.lib import render_rop

import hou


class ExtractRedshiftProxy(publish.Extractor):

    label = "Extract FilmBox FBX"
    families = ["filmboxfbx"]
    hosts = ["houdini"]

    # Usually you will use this value as default
    order = pyblish.api.ExtractorOrder + 0.1

    # overrides Extractor.process()
    def process(self, instance):

        # get rop node
        ropnode = hou.node(instance.data.get("instance_node"))

        # render rop
        render_rop(ropnode)

        # get required data
        file_name, staging_dir = self.get_paths_data(ropnode)
        representation = self.get_representation(instance,
                                                 file_name,
                                                 staging_dir)

        # set value type for 'representations' key to list
        if "representations" not in instance.data:
            instance.data["representations"] = []

        # update instance data
        instance.data["stagingDir"] = staging_dir
        instance.data["representations"].append(representation)

    def get_paths_data(self, ropnode):
        # Get the filename from the filename parameter
        output = ropnode.evalParm("sopoutput")

        staging_dir = os.path.normpath(os.path.dirname(output))

        file_name = os.path.basename(output)

        self.log.info("Writing FBX '%s' to '%s'" % (file_name,
                                                    staging_dir))

        return file_name, staging_dir

    def get_representation(self, instance,
                           file_name, staging_dir):

        representation = {
            "name": "fbx",
            "ext": "fbx",
            "files": file_name,
            "stagingDir": staging_dir,
        }

        # A single frame may also be rendered without start/end frame.
        if "frameStart" in instance.data and "frameEnd" in instance.data:
            representation["frameStart"] = instance.data["frameStart"]
            representation["frameEnd"] = instance.data["frameEnd"]

        return representation
