# -*- coding: utf-8 -*-
"""Maya look collector."""
import re
import os
import glob

from maya import cmds  # noqa
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


def get_pxr_multitexture_file_attrs(node):
    attrs = []
    for i in range(9):
        if cmds.attributeQuery("filename{}".format(i), node=node, ex=True):
            file = cmds.getAttr("{}.filename{}".format(node, i))
            if file:
                attrs.append("filename{}".format(i))
    return attrs


FILE_NODES = {
    # maya
    "file": "fileTextureName",
    # arnold (mtoa)
    "aiImage": "filename",
    # redshift
    "RedshiftNormalMap": "tex0",
    # renderman
    "PxrBump": "filename",
    "PxrNormalMap": "filename",
    "PxrMultiTexture": get_pxr_multitexture_file_attrs,
    "PxrPtexture": "filename",
    "PxrTexture": "filename"
}

RENDER_SET_TYPES = [
    "VRayDisplacement",
    "VRayLightMesh",
    "VRayObjectProperties",
    "RedshiftObjectId",
    "RedshiftMeshParameters",
]

# Keep only node types that actually exist
all_node_types = set(cmds.allNodeTypes())
for node_type in list(FILE_NODES.keys()):
    if node_type not in all_node_types:
        FILE_NODES.pop(node_type)

for node_type in RENDER_SET_TYPES:
    if node_type not in all_node_types:
        RENDER_SET_TYPES.remove(node_type)
del all_node_types

# Cache pixar dependency node types so we can perform a type lookup against it
PXR_NODES = set()
if cmds.pluginInfo("RenderMan_for_Maya", query=True, loaded=True):
    PXR_NODES = set(
        cmds.pluginInfo("RenderMan_for_Maya",
                        query=True,
                        dependNode=True)
    )


def get_attributes(dictionary, attr, node=None):
    # type: (dict, str, str) -> list
    if callable(dictionary[attr]):
        val = dictionary[attr](node)
    else:
        val = dictionary.get(attr, [])

    return val if isinstance(val, list) else [val]


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
            if attr in SHAPE_ATTRS or \
                    attr not in SHAPE_ATTRS and attr.startswith('ai'):
                result.append(attr)
    return result


def node_uses_image_sequence(node, node_path):
    # type: (str, str) -> bool
    """Return whether file node uses an image sequence or single image.

    Determine if a node uses an image sequence or just a single image,
    not always obvious from its file path alone.

    Args:
        node (str): Name of the Maya node
        node_path (str): The file path of the node

    Returns:
        bool: True if node uses an image sequence

    """

    # useFrameExtension indicates an explicit image sequence
    try:
        use_frame_extension = cmds.getAttr('%s.useFrameExtension' % node)
    except ValueError:
        use_frame_extension = False
    if use_frame_extension:
        return True

    # The following tokens imply a sequence
    patterns = ["<udim>", "<tile>", "<uvtile>",
                "u<u>_v<v>", "<frame0", "<f4>"]
    node_path_lowered = node_path.lower()
    return any(pattern in node_path_lowered for pattern in patterns)


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
        "<frame0": "<frame0\d+>",
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
    # type: (str) -> list
    """Get the file path used by a Maya file node.

    Args:
        node (str): Name of the Maya file node

    Returns:
        list: the file paths in use

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

    try:
        file_attributes = get_attributes(
            FILE_NODES, cmds.nodeType(node), node)
    except AttributeError:
        file_attributes = "fileTextureName"

    files = []
    for file_attr in file_attributes:
        if cmds.attributeQuery(file_attr, node=node, exists=True):
            files.append(cmds.getAttr("{}.{}".format(node, file_attr)))

    return files


def get_file_node_files(node):
    """Return the file paths related to the file node

    Note:
        Will only return existing files. Returns an empty list
        if not valid existing files are linked.

    Returns:
        list: List of full file paths.

    """
    paths = get_file_node_paths(node)

    # For sequences get all files and filter to only existing files
    result = []
    for path in paths:
        if node_uses_image_sequence(node, path):
            glob_pattern = seq_to_glob(path)
            result.extend(glob.glob(glob_pattern))
        elif os.path.exists(path):
            result.append(path)

    return result


class CollectLook(pyblish.api.InstancePlugin):
    """Collect look data for instance.

    For the shapes/transforms of the referenced object to collect look for
    retrieve the user-defined attributes (like V-ray attributes) and their
    values as they were created in the current scene.

    For the members of the instance collect the sets (shadingEngines and
    other sets, e.g. VRayDisplacement) they are in along with the exact
    membership relations.

    Collects:
        lookAttributes (list): Nodes in instance with their altered attributes
        lookSetRelations (list): Sets and their memberships
        lookSets (list): List of set names included in the look

    """

    order = pyblish.api.CollectorOrder + 0.2
    families = ["look"]
    label = "Collect Look"
    hosts = ["maya"]
    maketx = True

    def process(self, instance):
        """Collect the Look in the instance with the correct layer settings"""
        renderlayer = instance.data.get("renderlayer", "defaultRenderLayer")
        with lib.renderlayer(renderlayer):
            self.collect(instance)

    def collect(self, instance):
        """Collect looks.

        Args:
            instance: Instance to collect.

        """
        self.log.debug("Looking for look associations "
                       "for %s" % instance.data['name'])

        # Lookup set (optimization)
        instance_lookup = set(cmds.ls(instance, long=True))

        # Discover related object sets
        self.log.debug("Gathering sets ...")
        sets = self.collect_sets(instance)

        # Lookup set (optimization)
        instance_lookup = set(cmds.ls(instance, long=True))

        self.log.debug("Gathering set relations ...")
        # Ensure iteration happen in a list to allow removing keys from the
        # dict within the loop
        for obj_set in list(sets):
            self.log.debug("From {}".format(obj_set))
            # Get all nodes of the current objectSet (shadingEngine)
            for member in cmds.ls(cmds.sets(obj_set, query=True), long=True):
                member_data = self.collect_member_data(member,
                                                       instance_lookup)
                if member_data:
                    # Add information of the node to the members list
                    sets[obj_set]["members"].append(member_data)

            # Remove sets that didn't have any members assigned in the end
            # Thus the data will be limited to only what we need.
            if not sets[obj_set]["members"]:
                self.log.debug(
                    "Removing redundant set information: {}".format(obj_set)
                )
                sets.pop(obj_set, None)

        self.log.debug("Gathering attribute changes to instance members..")
        attributes = self.collect_attributes_changed(instance)

        # Store data on the instance
        instance.data["lookData"] = {
            "attributes": attributes,
            "relationships": sets
        }

        # Collect file nodes used by shading engines (if we have any)
        files = []
        look_sets = list(sets.keys())
        shader_attrs = [
            "surfaceShader",
            "volumeShader",
            "displacementShader",
            "aiSurfaceShader",
            "aiVolumeShader",
            "rman__surface",
            "rman__displacement"
        ]
        if look_sets:
            self.log.debug("Found look sets: {}".format(look_sets))

            # Get all material attrs for all look sets to retrieve their inputs
            existing_attrs = []
            for look in look_sets:
                for attr in shader_attrs:
                    if cmds.attributeQuery(attr, node=look, exists=True):
                        existing_attrs.append("{}.{}".format(look, attr))

            materials = cmds.listConnections(existing_attrs,
                                             source=True,
                                             destination=False) or []

            self.log.debug("Found materials:\n{}".format(materials))

            self.log.debug("Found the following sets:\n{}".format(look_sets))
            # Get the entire node chain of the look sets
            # history = cmds.listHistory(look_sets, allConnections=True)
            # if materials list is empty, listHistory() will crash with
            # RuntimeError
            history = set()
            if materials:
                history = set(
                    cmds.listHistory(materials, allConnections=True))

            # Since we retrieved history only of the connected materials
            # connected to the look sets above we now add direct history
            # for some of the look sets directly
            # handling render attribute sets

            # Maya (at least 2024) crashes with Warning when render set type
            # isn't available. cmds.ls() will return empty list
            if RENDER_SET_TYPES:
                render_sets = cmds.ls(look_sets, type=RENDER_SET_TYPES)
                if render_sets:
                    history.update(
                        cmds.listHistory(render_sets,
                                         future=False,
                                         pruneDagObjects=True)
                        or []
                    )

            # Ensure unique entries only
            history = list(history)

            files = cmds.ls(history,
                            # It's important only node types are passed that
                            # exist (e.g. for loaded plugins) because otherwise
                            # the result will turn back empty
                            type=list(FILE_NODES.keys()),
                            long=True)

            # Sort for log readability
            files.sort()

        self.log.debug("Collected file nodes:\n{}".format(files))
        # Collect textures if any file nodes are found
        resources = []
        for node in files:  # sort for log readability
            resources.extend(self.collect_resources(node))
        instance.data["resources"] = resources
        self.log.debug("Collected resources: {}".format(resources))

        # Log warning when no relevant sets were retrieved for the look.
        if (
            not instance.data["lookData"]["relationships"]
            and "model" not in self.families
        ):
            self.log.warning("No sets found for the nodes in the "
                             "instance: %s" % instance[:])

        # Ensure unique shader sets
        # Add shader sets to the instance for unify ID validation
        instance.extend(shader for shader in look_sets if shader
                        not in instance_lookup)

        self.log.debug("Collected look for %s" % instance)

    def collect_sets(self, instance):
        """Collect all objectSets which are of importance for publishing

        It checks if all nodes in the instance are related to any objectSet
        which need to be

        Args:
            instance (list): all nodes to be published

        Returns:
            dict
        """

        sets = {}
        for node in instance:
            related_sets = lib.get_related_sets(node)
            if not related_sets:
                continue

            for objset in related_sets:
                if objset in sets:
                    continue

                sets[objset] = {"uuid": lib.get_id(objset), "members": list()}

        return sets

    def collect_member_data(self, member, instance_members):
        """Get all information of the node
        Args:
            member (str): the name of the node to check
            instance_members (set): the collected instance members

        Returns:
            dict

        """

        node, components = (member.rsplit(".", 1) + [None])[:2]

        # Only include valid members of the instance
        if node not in instance_members:
            return

        node_id = lib.get_id(node)
        if not node_id:
            self.log.error("Member '{}' has no attribute 'cbId'".format(node))
            return

        member_data = {"name": node, "uuid": node_id}
        if components:
            member_data["components"] = components

        return member_data

    def collect_attributes_changed(self, instance):
        """Collect all userDefined attributes which have changed

        Each node gets checked for user defined attributes which have been
        altered during development. Each changes gets logged in a dictionary

        [{name: node,
          uuid: uuid,
          attributes: {attribute: value}}]

        Args:
            instance (list): all nodes which will be published

        Returns:
            list
        """

        attributes = []
        for node in instance:

            # Collect changes to "custom" attributes
            node_attrs = get_look_attrs(node)

            # Only include if there are any properties we care about
            if not node_attrs:
                continue

            self.log.debug(
                "Node \"{0}\" attributes: {1}".format(node, node_attrs)
            )

            node_attributes = {}
            for attr in node_attrs:
                if not cmds.attributeQuery(attr, node=node, exists=True):
                    continue
                attribute = "{}.{}".format(node, attr)
                # We don't support mixed-type attributes yet.
                if cmds.attributeQuery(attr, node=node, multi=True):
                    self.log.warning("Attribute '{}' is mixed-type and is "
                                     "not supported yet.".format(attribute))
                    continue
                if cmds.getAttr(attribute, type=True) == "message":
                    continue
                node_attributes[attr] = cmds.getAttr(attribute, asString=True)
            # Only include if there are any properties we care about
            if not node_attributes:
                continue
            attributes.append({"name": node,
                               "uuid": lib.get_id(node),
                               "attributes": node_attributes})

        return attributes

    def collect_resources(self, node):
        """Collect the link to the file(s) used (resource)
        Args:
            node (str): name of the node

        Returns:
            dict
        """
        if cmds.nodeType(node) not in FILE_NODES:
            self.log.error(
                "Unsupported file node: {}".format(cmds.nodeType(node)))
            raise AssertionError("Unsupported file node")

        self.log.debug(
            "Collecting resource: {} ({})".format(node, cmds.nodeType(node))
        )

        attributes = get_attributes(FILE_NODES, cmds.nodeType(node), node)
        for attribute in attributes:
            source = cmds.getAttr("{}.{}".format(
                node,
                attribute
            ))

            self.log.debug("  - file source: {}".format(source))
            color_space_attr = "{}.colorSpace".format(node)
            try:
                color_space = cmds.getAttr(color_space_attr)
            except ValueError:
                # node doesn't have colorspace attribute
                color_space = "Raw"

            # Compare with the computed file path, e.g. the one with
            # the <UDIM> pattern in it, to generate some logging information
            # about this difference
            # Only for file nodes with `fileTextureName` attribute
            if attribute == "fileTextureName":
                computed_source = cmds.getAttr(
                    "{}.computedFileTextureNamePattern".format(node)
                )
                if source != computed_source:
                    self.log.debug("Detected computed file pattern difference "
                                   "from original pattern: {0} "
                                   "({1} -> {2})".format(node,
                                                         source,
                                                         computed_source))

            # renderman allows nodes to have filename attribute empty while
            # you can have another incoming connection from different node.
            if not source and cmds.nodeType(node) in PXR_NODES:
                self.log.debug("Renderman: source is empty, skipping...")
                continue
            # We replace backslashes with forward slashes because V-Ray
            # can't handle the UDIM files with the backslashes in the
            # paths as the computed patterns
            source = source.replace("\\", "/")

            files = get_file_node_files(node)
            if len(files) == 0:
                self.log.debug("No valid files found from node `%s`" % node)

            self.log.debug("collection of resource done:")
            self.log.debug("  - node: {}".format(node))
            self.log.debug("  - attribute: {}".format(attribute))
            self.log.debug("  - source: {}".format(source))
            self.log.debug("  - file: {}".format(files))
            self.log.debug("  - color space: {}".format(color_space))

            # Define the resource
            yield {
                "node": node,
                # here we are passing not only attribute, but with node again
                # this should be simplified and changed extractor.
                "attribute": "{}.{}".format(node, attribute),
                "source": source,  # required for resources
                "files": files,
                "color_space": color_space
            }  # required for resources


class CollectModelRenderSets(CollectLook):
    """Collect render attribute sets for model instance.

    Collects additional render attribute sets so they can be
    published with model.

    """

    order = pyblish.api.CollectorOrder + 0.21
    families = ["model"]
    label = "Collect Model Render Sets"
    hosts = ["maya"]
    maketx = True

    def collect_sets(self, instance):
        """Collect all related objectSets except shadingEngines

        Args:
            instance (list): all nodes to be published

        Returns:
            dict
        """

        sets = {}
        for node in instance:
            related_sets = lib.get_related_sets(node)
            if not related_sets:
                continue

            for objset in related_sets:
                if objset in sets:
                    continue

                if "shadingEngine" in cmds.nodeType(objset, inherited=True):
                    continue

                sets[objset] = {"uuid": lib.get_id(objset), "members": list()}

        return sets
