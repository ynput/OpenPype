import os
import re

from maya import cmds

import pyblish.api

from colorbleed.maya import lib


SETTINGS = {"renderDensity",
            "renderWidth",
            "renderLength",
            "increaseRenderBounds",
            "imageSearchPath",
            "cbId"}


class CollectYetiRig(pyblish.api.InstancePlugin):
    """Collect all information of the Yeti Rig"""

    order = pyblish.api.CollectorOrder + 0.4
    label = "Collect Yeti Rig"
    families = ["colorbleed.yetiRig"]
    hosts = ["maya"]

    def process(self, instance):

        assert "input_SET" in instance.data["setMembers"], (
            "Yeti Rig must have an input_SET")

        # Get the input meshes information
        input_content = cmds.ls(cmds.sets("input_SET", query=True), long=True)

        # Include children
        input_content += cmds.listRelatives(input_content,
                                            allDescendents=True,
                                            fullPath=True) or []

        # Ignore intermediate objects
        input_content = cmds.ls(input_content, long=True, noIntermediate=True)

        # Store all connections
        connections = cmds.listConnections(input_content,
                                           source=True,
                                           destination=False,
                                           connections=True,
                                           # Only allow inputs from dagNodes
                                           # (avoid display layers, etc.)
                                           type="dagNode",
                                           plugs=True) or []

        # Group per source, destination pair. We need to reverse the connection
        # list as it comes in with the shape used to query first while that
        # shape is the destination of the connection
        grouped = [(connections[i+1], item) for i, item in
                   enumerate(connections) if i % 2 == 0]

        inputs = []
        for src, dest in grouped:
            source_node, source_attr = src.split(".", 1)
            dest_node, dest_attr = dest.split(".", 1)

            inputs.append({"connections": [source_attr, dest_attr],
                           "sourceID": lib.get_id(source_node),
                           "destinationID": lib.get_id(dest_node)})

        # Collect any textures if used
        yeti_resources = []
        yeti_nodes = cmds.ls(instance[:], type="pgYetiMaya", long=True)
        for node in yeti_nodes:
            # Get Yeti resources (textures)
            resources = self.get_yeti_resources(node)
            yeti_resources.extend(resources)

        instance.data["rigsettings"] = {"inputs": inputs}

        instance.data["resources"] = yeti_resources

        # Force frame range for export
        instance.data["startFrame"] = 1
        instance.data["endFrame"] = 1

    def get_yeti_resources(self, node):
        """Get all resource file paths

        If a texture is a sequence it gathers all sibling files to ensure
        the texture sequence is complete.

        References can be used in the Yeti graph, this means that it is
        possible to load previously caches files. The information will need
        to be stored and, if the file not publish, copied to the resource
        folder.

        Args:
            node (str): node name of the pgYetiMaya node

        Returns:
            list
        """
        resources = []
        image_search_path = cmds.getAttr("{}.imageSearchPath".format(node))

        # List all related textures
        texture_filenames = cmds.pgYetiCommand(node, listTextures=True)
        self.log.info("Found %i texture(s)" % len(texture_filenames))

        # Get all reference nodes
        reference_nodes = cmds.pgYetiGraph(node,
                                           listNodes=True,
                                           type="reference")
        self.log.info("Found %i reference node(s)" % len(reference_nodes))

        if texture_filenames and not image_search_path:
            raise ValueError("pgYetiMaya node '%s' is missing the path to the "
                             "files in the 'imageSearchPath "
                             "atttribute'" % node)

        # Collect all texture files
        for texture in texture_filenames:
            item = {"files": [], "source": texture, "node": node}
            texture_filepath = os.path.join(image_search_path, texture)
            if len(texture.split(".")) > 2:

                # For UDIM based textures (tiles)
                if "<UDIM>" in texture:
                    sequences = self.get_sequence(texture_filepath,
                                                  pattern="<UDIM>")
                    item["files"].extend(sequences)

                # Based textures (animated masks f.e)
                elif "%04d" in texture:
                    sequences = self.get_sequence(texture_filepath,
                                                  pattern="%04d")
                    item["files"].extend(sequences)
                # Assuming it is a fixed name
                else:
                    item["files"].append(texture_filepath)
            else:
                item["files"].append(texture_filepath)

            resources.append(item)

        # Collect all referenced files
        for reference_node in reference_nodes:
            ref_file = cmds.pgYetiGraph(node,
                                        node=reference_node,
                                        param="reference_file",
                                        getParamValue=True)

            if not os.path.isfile(ref_file):
                raise RuntimeError("Reference file must be a full file path!")

            # Create resource dict
            item = {"files": [],
                    "source": ref_file,
                    "node": node,
                    "graphnode": reference_node,
                    "param": "reference_file"}

            ref_file_name = os.path.basename(ref_file)
            if "%04d" in ref_file_name:
                ref_files = self.get_sequence(ref_file)
                item["files"].extend(ref_files)
            else:
                item["files"].append(ref_file)

            resources.append(item)

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

        escaped = re.escape(filename)
        re_pattern = escaped.replace(pattern, "-?[0-9]+")

        source_dir = os.path.dirname(filename)
        files = [f for f in os.listdir(source_dir)
                 if re.match(re_pattern, f)]

        pattern = [clique.PATTERNS["frames"]]
        collection, remainder = clique.assemble(files, patterns=pattern)

        return collection
