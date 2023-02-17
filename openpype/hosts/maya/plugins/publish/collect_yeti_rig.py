import os
import re

from maya import cmds

import pyblish.api

from openpype.hosts.maya.api import lib


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
    families = ["yetiRig"]
    hosts = ["maya"]

    def process(self, instance):

        assert "input_SET" in instance.data["setMembers"], (
            "Yeti Rig must have an input_SET")

        input_connections = self.collect_input_connections(instance)

        # Collect any textures if used
        yeti_resources = []
        yeti_nodes = cmds.ls(instance[:], type="pgYetiMaya", long=True)
        for node in yeti_nodes:
            # Get Yeti resources (textures)
            resources = self.get_yeti_resources(node)
            yeti_resources.extend(resources)

        instance.data["rigsettings"] = {"inputs": input_connections}

        instance.data["resources"] = yeti_resources

        # Force frame range for yeti cache export for the rig
        start = cmds.playbackOptions(query=True, animationStartTime=True)
        for key in ["frameStart", "frameEnd",
                    "frameStartHandle", "frameEndHandle"]:
            instance.data[key] = start
        instance.data["preroll"] = 0

    def collect_input_connections(self, instance):
        """Collect the inputs for all nodes in the input_SET"""

        # Get the input meshes information
        input_content = cmds.ls(cmds.sets("input_SET", query=True), long=True)

        # Include children
        input_content += cmds.listRelatives(input_content,
                                            allDescendents=True,
                                            fullPath=True) or []

        # Ignore intermediate objects
        input_content = cmds.ls(input_content, long=True, noIntermediate=True)
        if not input_content:
            return []

        # Store all connections
        connections = cmds.listConnections(input_content,
                                           source=True,
                                           destination=False,
                                           connections=True,
                                           # Only allow inputs from dagNodes
                                           # (avoid display layers, etc.)
                                           type="dagNode",
                                           plugs=True) or []
        connections = cmds.ls(connections, long=True)      # Ensure long names

        inputs = []
        for dest, src in lib.pairwise(connections):
            source_node, source_attr = src.split(".", 1)
            dest_node, dest_attr = dest.split(".", 1)

            # Ensure the source of the connection is not included in the
            # current instance's hierarchy. If so, we ignore that connection
            # as we will want to preserve it even over a publish.
            if source_node in instance:
                self.log.debug("Ignoring input connection between nodes "
                               "inside the instance: %s -> %s" % (src, dest))
                continue

            inputs.append({"connections": [source_attr, dest_attr],
                           "sourceID": lib.get_id(source_node),
                           "destinationID": lib.get_id(dest_node)})

        return inputs

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

        image_search_paths = cmds.getAttr("{}.imageSearchPath".format(node))
        texture_filenames = []
        if image_search_paths:


            # TODO: Somehow this uses OS environment path separator, `:` vs `;`
            # Later on check whether this is pipeline OS cross-compatible.
            image_search_paths = [p for p in
                                  image_search_paths.split(os.path.pathsep) if p]

            # find all ${TOKEN} tokens and replace them with $TOKEN env. variable
            image_search_paths = self._replace_tokens(image_search_paths)

            # List all related textures
            texture_filenames = cmds.pgYetiCommand(node, listTextures=True)
            self.log.info("Found %i texture(s)" % len(texture_filenames))

        # Get all reference nodes
        reference_nodes = cmds.pgYetiGraph(node,
                                           listNodes=True,
                                           type="reference")
        self.log.info("Found %i reference node(s)" % len(reference_nodes))

        if texture_filenames and not image_search_paths:
            raise ValueError("pgYetiMaya node '%s' is missing the path to the "
                             "files in the 'imageSearchPath "
                             "atttribute'" % node)

        # Collect all texture files
        # find all ${TOKEN} tokens and replace them with $TOKEN env. variable
        texture_filenames = self._replace_tokens(texture_filenames)
        for texture in texture_filenames:

            files = []
            if os.path.isabs(texture):
                self.log.debug("Texture is absolute path, ignoring "
                               "image search paths for: %s" % texture)
                files = self.search_textures(texture)
            else:
                for root in image_search_paths:
                    filepath = os.path.join(root, texture)
                    files = self.search_textures(filepath)
                    if files:
                        # Break out on first match in search paths..
                        break

            if not files:
                self.log.warning(
                    "No texture found for: %s "
                    "(searched: %s)" % (texture, image_search_paths))

            item = {
                "files": files,
                "source": texture,
                "node": node
            }

            resources.append(item)

        # For now validate that every texture has at least a single file
        # resolved. Since a 'resource' does not have the requirement of having
        # a `files` explicitly mapped it's not explicitly validated.
        # TODO: Validate this as a validator
        invalid_resources = []
        for resource in resources:
            if not resource['files']:
                invalid_resources.append(resource)
        if invalid_resources:
            raise RuntimeError("Invalid resources")

        # Collect all referenced files
        for reference_node in reference_nodes:
            ref_file = cmds.pgYetiGraph(node,
                                        node=reference_node,
                                        param="reference_file",
                                        getParamValue=True)

            # Create resource dict
            item = {
                "source": ref_file,
                "node": node,
                "graphnode": reference_node,
                "param": "reference_file",
                "files": []
            }

            ref_file_name = os.path.basename(ref_file)
            if "%04d" in ref_file_name:
                item["files"] = self.get_sequence(ref_file)
            else:
                if os.path.exists(ref_file) and os.path.isfile(ref_file):
                    item["files"] = [ref_file]

            if not item["files"]:
                self.log.warning("Reference node '%s' has no valid file "
                                 "path set: %s" % (reference_node, ref_file))
                # TODO: This should allow to pass and fail in Validator instead
                raise RuntimeError("Reference node  must be a full file path!")

            resources.append(item)

        return resources

    def search_textures(self, filepath):
        """Search all texture files on disk.

        This also parses to full sequences for those with dynamic patterns
        like <UDIM> and %04d in the filename.

        Args:
            filepath (str): The full path to the file, including any
                dynamic patterns like <UDIM> or %04d

        Returns:
            list: The files found on disk

        """
        filename = os.path.basename(filepath)

        # Collect full sequence if it matches a sequence pattern
        if len(filename.split(".")) > 2:

            # For UDIM based textures (tiles)
            if "<UDIM>" in filename:
                sequences = self.get_sequence(filepath,
                                              pattern="<UDIM>")
                if sequences:
                    return sequences

            # Frame/time - Based textures (animated masks f.e)
            elif "%04d" in filename:
                sequences = self.get_sequence(filepath,
                                              pattern="%04d")
                if sequences:
                    return sequences

        # Assuming it is a fixed name (single file)
        if os.path.exists(filepath):
            return [filepath]

        return []

    def get_sequence(self, filepath, pattern="%04d"):
        """Get sequence from filename.

        This will only return files if they exist on disk as it tries
        to collect the sequence using the filename pattern and searching
        for them on disk.

        Supports negative frame ranges like -001, 0000, 0001 and -0001,
        0000, 0001.

        Arguments:
            filepath (str): The full path to filename containing the given
            pattern.
            pattern (str): The pattern to swap with the variable frame number.

        Returns:
            list: file sequence.

        """
        import clique

        escaped = re.escape(filepath)
        re_pattern = escaped.replace(pattern, "-?[0-9]+")

        source_dir = os.path.dirname(filepath)
        files = [f for f in os.listdir(source_dir)
                 if re.match(re_pattern, f)]

        pattern = [clique.PATTERNS["frames"]]
        collection, remainder = clique.assemble(files, patterns=pattern)

        return collection

    def _replace_tokens(self, strings):
        env_re = re.compile(r"\$\{(\w+)\}")

        replaced = []
        for s in strings:
            matches = re.finditer(env_re, s)
            for m in matches:
                try:
                    s = s.replace(m.group(), os.environ[m.group(1)])
                except KeyError:
                    msg = "Cannot find requested {} in environment".format(
                        m.group(1))
                    self.log.error(msg)
                    raise RuntimeError(msg)
            replaced.append(s)
        return replaced
