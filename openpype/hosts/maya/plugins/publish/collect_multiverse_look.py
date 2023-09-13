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
COLOUR_SPACES = ['sRGB', 'linear', 'auto']
MIPMAP_EXTENSIONS = ['tdl']


class _NodeTypeAttrib(object):
    """docstring for _NodeType"""

    def __init__(self, name, fname, computed_fname=None, colour_space=None):
        self.name = name
        self.fname = fname
        self.computed_fname = computed_fname or fname
        self.colour_space = colour_space or "colorSpace"

    def get_fname(self, node):
        return "{}.{}".format(node, self.fname)

    def get_computed_fname(self, node):
        return "{}.{}".format(node, self.computed_fname)

    def get_colour_space(self, node):
        return "{}.{}".format(node, self.colour_space)

    def __str__(self):
        return "_NodeTypeAttrib(name={}, fname={}, "
        "computed_fname={}, colour_space={})".format(
            self.name, self.fname, self.computed_fname, self.colour_space)


NODETYPES = {
    "file": [_NodeTypeAttrib("file", "fileTextureName",
                             "computedFileTextureNamePattern")],
    "aiImage": [_NodeTypeAttrib("aiImage", "filename")],
    "RedshiftNormalMap": [_NodeTypeAttrib("RedshiftNormalMap", "tex0")],
    "dlTexture": [_NodeTypeAttrib("dlTexture", "textureFile",
                                  None, "textureFile_meta_colorspace")],
    "dlTriplanar": [_NodeTypeAttrib("dlTriplanar", "colorTexture",
                                    None, "colorTexture_meta_colorspace"),
                    _NodeTypeAttrib("dlTriplanar", "floatTexture",
                                    None, "floatTexture_meta_colorspace"),
                    _NodeTypeAttrib("dlTriplanar", "heightTexture",
                                    None, "heightTexture_meta_colorspace")]
}


def get_file_paths_for_node(node):
    """Gets all the file paths in this node.

    Returns all filepaths that this node references. Some node types only
    reference one, but others, like dlTriplanar, can reference 3.

    Args:
        node (str): Name of the Maya node

    Returns
        list(str): A list with all evaluated maya attributes for filepaths.
    """

    node_type = cmds.nodeType(node)
    if node_type not in NODETYPES:
        return []

    paths = []
    for node_type_attr in NODETYPES[node_type]:
        fname = cmds.getAttr("{}.{}".format(node, node_type_attr.fname))
        paths.append(fname)
    return paths


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
    paths = get_file_node_paths(node)
    paths = [path.lower() for path in paths]

    # The following tokens imply a sequence
    patterns = ["<udim>", "<tile>", "<uvtile>", "u<u>_v<v>", "<frame0"]

    def pattern_in_paths(patterns, paths):
        """Helper function for checking to see if a pattern is contained
        in the list of paths"""
        for pattern in patterns:
            for path in paths:
                if pattern in path:
                    return True
        return False

    node_type = cmds.nodeType(node)
    if node_type == 'dlTexture':
        return (cmds.getAttr('{}.useImageSequence'.format(node)) or
                pattern_in_paths(patterns, paths))
    elif node_type == "file":
        return (cmds.getAttr('{}.useFrameExtension'.format(node)) or
                pattern_in_paths(patterns, paths))
    return False


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
        "<frame0": "<frame0\d+>",  # noqa - copied from collect_look.py
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


def get_file_node_paths(node):
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
            return [texture_pattern]

    return get_file_paths_for_node(node)


def get_file_node_files(node):
    """Return the file paths related to the file node

    Note:
        Will only return existing files. Returns an empty list
        if not valid existing files are linked.

    Returns:
        list: List of full file paths.

    """

    paths = get_file_node_paths(node)
    paths = [cmds.workspace(expandName=path) for path in paths]
    if node_uses_image_sequence(node):
        globs = []
        for path in paths:
            globs += glob.glob(seq_to_glob(path))
        return globs
    else:
        return list(filter(lambda x: os.path.exists(x), paths))


def get_mipmap(fname):
    for colour_space in COLOUR_SPACES:
        for mipmap_ext in MIPMAP_EXTENSIONS:
            mipmap_fname = '.'.join([fname, colour_space, mipmap_ext])
            if os.path.exists(mipmap_fname):
                return mipmap_fname
    return None


def is_mipmap(fname):
    ext = os.path.splitext(fname)[1][1:]
    if ext in MIPMAP_EXTENSIONS:
        return True
    return False


class CollectMultiverseLookData(pyblish.api.InstancePlugin):
    """Collect Multiverse Look

    Searches through the overrides finding all material overrides. From there
    it extracts the shading group and then finds all texture files in the
    shading group network. It also checks for mipmap versions of texture files
    and adds them to the resources to get published.

    """

    order = pyblish.api.CollectorOrder + 0.2
    label = 'Collect Multiverse Look'
    families = ["mvLook"]

    def process(self, instance):
        # Load plugin first
        cmds.loadPlugin("MultiverseForMaya", quiet=True)
        import multiverse

        self.log.debug("Processing mvLook for '{}'".format(instance))

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

        sets = {}
        instance.data["resources"] = []
        publishMipMap = instance.data["publishMipMap"]

        for node in nodes:
            self.log.debug("Getting resources for '{}'".format(node))

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
                    history = cmds.listHistory(
                        shadingGroup, allConnections=True)

                    # We need to iterate over node_types since `cmds.ls` may
                    # error out if we don't have the appropriate plugin loaded.
                    files = []
                    for node_type in NODETYPES.keys():
                        files += cmds.ls(history,
                                         type=node_type,
                                         long=True)

                    for f in files:
                        resources = self.collect_resource(f, publishMipMap)
                        instance.data["resources"] += resources

                elif isinstance(matOver, multiverse.MaterialSourceUsdPath):
                    # TODO: Handle this later.
                    pass

        # Store data on the instance for validators, extractos, etc.
        instance.data["lookData"] = {
            "attributes": [],
            "relationships": sets
        }

    def collect_resource(self, node, publishMipMap):
        """Collect the link to the file(s) used (resource)
        Args:
            node (str): name of the node

        Returns:
            dict
        """

        node_type = cmds.nodeType(node)
        self.log.debug("processing: {}/{}".format(node, node_type))

        if node_type not in NODETYPES:
            self.log.error("Unsupported file node: {}".format(node_type))
            raise AssertionError("Unsupported file node")

        resources = []
        for node_type_attr in NODETYPES[node_type]:
            fname_attrib = node_type_attr.get_fname(node)
            computed_fname_attrib = node_type_attr.get_computed_fname(node)
            colour_space_attrib = node_type_attr.get_colour_space(node)

            source = cmds.getAttr(fname_attrib)
            color_space = "Raw"
            try:
                color_space = cmds.getAttr(colour_space_attrib)
            except ValueError:
                # node doesn't have colorspace attribute, use "Raw" from before
                pass
            # Compare with the computed file path, e.g. the one with the <UDIM>
            # pattern in it, to generate some logging information about this
            # difference
            # computed_attribute = "{}.computedFileTextureNamePattern".format(node)  # noqa
            computed_source = cmds.getAttr(computed_fname_attrib)
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
            files = self.handle_files(files, publishMipMap)
            if len(files) == 0:
                self.log.error("No valid files found from node `%s`" % node)

            self.log.debug("collection of resource done:")
            self.log.debug("  - node: {}".format(node))
            self.log.debug("  - attribute: {}".format(fname_attrib))
            self.log.debug("  - source: {}".format(source))
            self.log.debug("  - file: {}".format(files))
            self.log.debug("  - color space: {}".format(color_space))

            # Define the resource
            resource = {"node": node,
                        "attribute": fname_attrib,
                        "source": source,  # required for resources
                        "files": files,
                        "color_space": color_space}  # required for resources
            resources.append(resource)
        return resources

    def handle_files(self, files, publishMipMap):
        """This will go through all the files and make sure that they are
        either already mipmapped or have a corresponding mipmap sidecar and
        add that to the list."""
        if not publishMipMap:
            return files

        extra_files = []
        self.log.debug("Expecting MipMaps, going to look for them.")
        for fname in files:
            self.log.debug("Checking '{}' for mipmaps".format(fname))
            if is_mipmap(fname):
                self.log.debug(" - file is already MipMap, skipping.")
                continue

            mipmap = get_mipmap(fname)
            if mipmap:
                self.log.debug(" mipmap found for '{}'".format(fname))
                extra_files.append(mipmap)
            else:
                self.log.warning(" no mipmap found for '{}'".format(fname))
        return files + extra_files
