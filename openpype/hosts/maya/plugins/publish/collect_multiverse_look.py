import glob
import os
import re

from maya import cmds
import pyblish.api
from openpype.hosts.maya.api import lib

SHAPE_ATTRS = ["castsShadows",
               "receiveShadows",
               "motionBlur",
               "primaryVisibility",
               "smoothShading",
               "visibleInReflections",
               "visibleInRefractions",
               "doubleSided",
               "opposite"]

SHAPE_ATTRS = set(SHAPE_ATTRS)

def get_look_attrs(node):
    """Returns attributes of a node that are important for the look.

    These are the "changed" attributes (those that have edits applied
    in the current scene).

    Returns:
        list: Attribute names to extract

    """
    # When referenced get only attributes that are "changed since file open"
    # which includes any reference edits, otherwise take *all* user defined
    # attributes
    is_referenced = cmds.referenceQuery(node, isNodeReferenced=True)
    result = cmds.listAttr(node, userDefined=True,
                           changedSinceFileOpen=is_referenced) or []

    # `cbId` is added when a scene is saved, ignore by default
    if "cbId" in result:
        result.remove("cbId")

    # For shapes allow render stat changes
    if cmds.objectType(node, isAType="shape"):
        attrs = cmds.listAttr(node, changedSinceFileOpen=True) or []
        for attr in attrs:
            if attr in SHAPE_ATTRS:
                result.append(attr)
            elif attr.startswith('ai'):
                result.append(attr)

    return result


def node_uses_image_sequence(node):
    """Return whether file node uses an image sequence or single image.

    Determine if a node uses an image sequence or just a single image,
    not always obvious from its file path alone.

    Args:
        node (str): Name of the Maya node

    Returns:
        bool: True if node uses an image sequence

    """

    # useFrameExtension indicates an explicit image sequence
    node_path = get_file_node_path(node).lower()

    # The following tokens imply a sequence
    patterns = ["<udim>", "<tile>", "<uvtile>", "u<u>_v<v>", "<frame0"]

    return (cmds.getAttr('%s.useFrameExtension' % node) or
            any(pattern in node_path for pattern in patterns))


def seq_to_glob(path):
    """Takes an image sequence path and returns it in glob format,
    with the frame number replaced by a '*'.

    Image sequences may be numerical sequences, e.g. /path/to/file.1001.exr
    will return as /path/to/file.*.exr.

    Image sequences may also use tokens to denote sequences, e.g.
    /path/to/texture.<UDIM>.tif will return as /path/to/texture.*.tif.

    Args:
        path (str): the image sequence path

    Returns:
        str: Return glob string that matches the filename pattern.

    """

    if path is None:
        return path

    # If any of the patterns, convert the pattern
    patterns = {
        "<udim>": "<udim>",
        "<tile>": "<tile>",
        "<uvtile>": "<uvtile>",
        "#": "#",
        "u<u>_v<v>": "<u>|<v>",
        "<frame0": "<frame0\d+>", #noqa - copied from collect_look.py
        "<f>": "<f>"
    }

    lower = path.lower()
    has_pattern = False
    for pattern, regex_pattern in patterns.items():
        if pattern in lower:
            path = re.sub(regex_pattern, "*", path, flags=re.IGNORECASE)
            has_pattern = True

    if has_pattern:
        return path

    base = os.path.basename(path)
    matches = list(re.finditer(r'\d+', base))
    if matches:
        match = matches[-1]
        new_base = '{0}*{1}'.format(base[:match.start()],
                                    base[match.end():])
        head = os.path.dirname(path)
        return os.path.join(head, new_base)
    else:
        return path


def get_file_node_path(node):
    """Get the file path used by a Maya file node.

    Args:
        node (str): Name of the Maya file node

    Returns:
        str: the file path in use

    """
    # if the path appears to be sequence, use computedFileTextureNamePattern,
    # this preserves the <> tag
    if cmds.attributeQuery('computedFileTextureNamePattern',
                           node=node,
                           exists=True):
        plug = '{0}.computedFileTextureNamePattern'.format(node)
        texture_pattern = cmds.getAttr(plug)

        patterns = ["<udim>",
                    "<tile>",
                    "u<u>_v<v>",
                    "<f>",
                    "<frame0",
                    "<uvtile>"]
        lower = texture_pattern.lower()
        if any(pattern in lower for pattern in patterns):
            return texture_pattern

    if cmds.nodeType(node) == 'aiImage':
        return cmds.getAttr('{0}.filename'.format(node))
    if cmds.nodeType(node) == 'RedshiftNormalMap':
        return cmds.getAttr('{}.tex0'.format(node))

    # otherwise use fileTextureName
    return cmds.getAttr('{0}.fileTextureName'.format(node))


def get_file_node_files(node):
    """Return the file paths related to the file node

    Note:
        Will only return existing files. Returns an empty list
        if not valid existing files are linked.

    Returns:
        list: List of full file paths.

    """

    path = get_file_node_path(node)
    path = cmds.workspace(expandName=path)
    if node_uses_image_sequence(node):
        glob_pattern = seq_to_glob(path)
        return glob.glob(glob_pattern)
    elif os.path.exists(path):
        return [path]
    else:
        return []


class CollectMultiverseLookData(pyblish.api.InstancePlugin):
    """Collect Multiverse Look

    """

    order = pyblish.api.CollectorOrder + 0.2
    label = 'Collect Multiverse Look'
    families = ["mvLook"]

    def process(self, instance):
        # Load plugin first
        cmds.loadPlugin("MultiverseForMaya", quiet=True)
        import multiverse

        self.log.info("Processing mvLook for '{}'".format(instance))

        nodes = set()
        for node in instance:
            # We want only mvUsdCompoundShape nodes.
            nodes_of_interest = cmds.ls(node,
                                        dag=True,
                                        shapes=False,
                                        type="mvUsdCompoundShape",
                                        noIntermediate=True,
                                        long=True)
            nodes.update(nodes_of_interest)

        files = []
        sets = {}
        instance.data["resources"] = []

        for node in nodes:
            self.log.info("Getting resources for '{}'".format(node))

            # We know what nodes need to be collected, now we need to
            # extract the materials overrides.
            overrides = multiverse.ListMaterialOverridePrims(node)
            for override in overrides:
                matOver = multiverse.GetMaterialOverride(node, override)

                if isinstance(matOver, multiverse.MaterialSourceShadingGroup):
                    # We now need to grab the shadingGroup so add it to the
                    # sets we pass down the pipe.
                    shadingGroup = matOver.shadingGroupName
                    self.log.debug("ShadingGroup = '{}'".format(shadingGroup))
                    sets[shadingGroup] = {"uuid": lib.get_id(
                        shadingGroup), "members": list()}

                    # The SG may reference files, add those too!
                    history = cmds.listHistory(shadingGroup)
                    files = cmds.ls(history, type="file", long=True)

                    for f in files:
                        resources = self.collect_resource(f)
                        instance.data["resources"].append(resources)

                elif isinstance(matOver, multiverse.MaterialSourceUsdPath):
                    # TODO: Handle this later.
                    pass

        # Store data on the instance for validators, extractos, etc.
        instance.data["lookData"] = {
            "attributes": [],
            "relationships": sets
        }

    def collect_resource(self, node):
        """Collect the link to the file(s) used (resource)
        Args:
            node (str): name of the node

        Returns:
            dict
        """

        self.log.debug("processing: {}".format(node))
        if cmds.nodeType(node) not in ["file", "aiImage", "RedshiftNormalMap"]:
            self.log.error(
                "Unsupported file node: {}".format(cmds.nodeType(node)))
            raise AssertionError("Unsupported file node")

        if cmds.nodeType(node) == 'file':
            self.log.debug("  - file node")
            attribute = "{}.fileTextureName".format(node)
            computed_attribute = "{}.computedFileTextureNamePattern".format(
                node)
        elif cmds.nodeType(node) == 'aiImage':
            self.log.debug("aiImage node")
            attribute = "{}.filename".format(node)
            computed_attribute = attribute
        elif cmds.nodeType(node) == 'RedshiftNormalMap':
            self.log.debug("RedshiftNormalMap node")
            attribute = "{}.tex0".format(node)
            computed_attribute = attribute

        source = cmds.getAttr(attribute)
        self.log.info("  - file source: {}".format(source))
        color_space_attr = "{}.colorSpace".format(node)
        try:
            color_space = cmds.getAttr(color_space_attr)
        except ValueError:
            # node doesn't have colorspace attribute
            color_space = "Raw"
        # Compare with the computed file path, e.g. the one with the <UDIM>
        # pattern in it, to generate some logging information about this
        # difference
        # computed_attribute = "{}.computedFileTextureNamePattern".format(node)
        computed_source = cmds.getAttr(computed_attribute)
        if source != computed_source:
            self.log.debug("Detected computed file pattern difference "
                           "from original pattern: {0} "
                           "({1} -> {2})".format(node,
                                                 source,
                                                 computed_source))

        # We replace backslashes with forward slashes because V-Ray
        # can't handle the UDIM files with the backslashes in the
        # paths as the computed patterns
        source = source.replace("\\", "/")

        files = get_file_node_files(node)
        if len(files) == 0:
            self.log.error("No valid files found from node `%s`" % node)

        self.log.info("collection of resource done:")
        self.log.info("  - node: {}".format(node))
        self.log.info("  - attribute: {}".format(attribute))
        self.log.info("  - source: {}".format(source))
        self.log.info("  - file: {}".format(files))
        self.log.info("  - color space: {}".format(color_space))

        # Define the resource
        return {"node": node,
                "attribute": attribute,
                "source": source,  # required for resources
                "files": files,
                "color_space": color_space}  # required for resources
