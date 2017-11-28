import os
import glob
import re

from maya import cmds

import pyblish.api
from avalon import api

from colorbleed.maya import lib


SETTINGS = {"renderDensity": 10.0,
            "renderWidth": 1.0,
            "renderLength": 1.0,
            "increaseRenderBounds": 0.1}


class CollectYetiProceduralData(pyblish.api.InstancePlugin):
    """Collect procedural data"""

    order = pyblish.api.CollectorOrder + 0.4
    families = ["colorbleed.yetiprocedural"]
    label = "Collect Yeti Procedural"
    hosts = ["maya"]

    def process(self, instance):

        # Collect animation data
        animation_data = lib.collect_animation_data()
        instance.data.update(animation_data)

        # We only want one frame to export if it is not animation
        if api.Session["AVALON_TASK"] != "animation":
            instance.data["startFrame"] = 1
            instance.data["endFrame"] = 1

        # Get all procedural nodes
        yeti_nodes = cmds.ls(instance[:], type="pgYetiMaya")

        # Collect any textures if used
        node_attrs = {}
        yeti_resources = []
        for node in yeti_nodes:
            resources = self.get_yeti_resources(node)
            yeti_resources.extend(resources)

            node_attrs[node] = {}
            for attr, value in SETTINGS.iteritems():
                current = cmds.getAttr("%s.%s" % (node, attr))
                node_attrs[node][attr] = current

        instance.data["settings"] = node_attrs
        instance.data["resources"] = yeti_resources

    def get_yeti_resources(self, node):
        """Get all texture file paths

        If a texture is a sequence it gathers all sibling files to ensure
        the texture sequence is complete.

        Args:
            node (str): node name of the pgYetiMaya node

        Returns:
            list
        """
        resources = []
        image_search_path = cmds.getAttr("{}.imageSearchPath".format(node))
        texture_filenames = cmds.pgYetiCommand(node, listTextures=True)

        if texture_filenames and not image_search_path:
            raise ValueError("pgYetiMaya node '%s' is missing the path to the "
                             "files in the 'imageSearchPath "
                             "atttribute'" % node)

        for texture in texture_filenames:
            node_resources = {"files": [], "source": texture, "node": node}
            texture_filepath = os.path.join(image_search_path, texture)
            if len(texture.split(".")) > 2:
                # For UDIM based textures (tiles)
                if "<UDIM>" in texture:
                    sequences = self.get_sequence(texture_filepath,
                                                  pattern="<UDIM>")
                    node_resources["node"].extend(sequences)

                # Based textures (animated masks f.e)
                elif "%04d" in texture:
                    sequences = self.get_sequence(texture_filepath,
                                                  pattern="%04d")
                    node_resources["node"].extend(sequences)
                # Assuming it is a fixed name
                else:
                    node_resources["node"].append(texture_filepath)
            else:
                node_resources["node"].append(texture_filepath)

            resources.append(node_resources)

        return resources

    def get_sequence(self, filename, pattern="%04d"):
        """Get sequence from filename

        Supports negative frame ranges like -001, 0000, 0001 and -0001,
        0000, 0001.

        Arguments:
            filename (str): The full path to filename containing the given
            pattern.
            pattern (str): The pattern to swap with the variable frame number.

        Returns:
            list: file sequence.

        """

        from avalon.vendor import clique

        glob_pattern = filename.replace(pattern, "*")

        escaped = re.escape(filename)
        re_pattern = escaped.replace(pattern, "-?[0-9]+")

        files = glob.glob(glob_pattern)
        files = [str(f) for f in files if re.match(re_pattern, f)]

        pattern = [clique.PATTERNS["frames"]]
        collection, remainer = clique.assemble(files, patterns=pattern)

        return collection
