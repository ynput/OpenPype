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

RENDERER_NODE_TYPES = [
    # redshift
    "RedshiftMeshParameters"
]

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


class CollectLook(pyblish.api.InstancePlugin):
    """Collect look data for instance.

    For the shapes/transforms of the referenced object to collect look for
    retrieve the user-defined attributes (like V-ray attributes) and their
    values as they were created in the current scene.

    For the members of the instance collect the sets (shadingEngines and
    other sets, e.g. VRayDisplacement) they are in along with the exact
    membership relations.

    Collects:
        lookAttribtutes (list): Nodes in instance with their altered attributes
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
        self.log.info("Looking for look associations "
                      "for %s" % instance.data['name'])

        # Discover related object sets
        self.log.info("Gathering sets..")
        sets = self.collect_sets(instance)

        # Lookup set (optimization)
        instance_lookup = set(cmds.ls(instance, long=True))

        self.log.info("Gathering set relations..")
        # Ensure iteration happen in a list so we can remove keys from the
        # dict within the loop

        # skipped types of attribute on render specific nodes
        disabled_types = ["message", "TdataCompound"]

        for obj_set in list(sets):
            self.log.debug("From {}".format(obj_set))

            # if node is specified as renderer node type, it will be
            # serialized with its attributes.
            if cmds.nodeType(obj_set) in RENDERER_NODE_TYPES:
                self.log.info("- {} is {}".format(
                    obj_set, cmds.nodeType(obj_set)))

                node_attrs = []

                # serialize its attributes so they can be recreated on look
                # load.
                for attr in cmds.listAttr(obj_set):
                    # skip publishedNodeInfo attributes as they break
                    # getAttr() and we don't need them anyway
                    if attr.startswith("publishedNodeInfo"):
                        continue

                    # skip attributes types defined in 'disabled_type' list
                    if cmds.getAttr("{}.{}".format(obj_set, attr), type=True) in disabled_types:  # noqa
                        continue

                    node_attrs.append((
                        attr,
                        cmds.getAttr("{}.{}".format(obj_set, attr)),
                        cmds.getAttr(
                            "{}.{}".format(obj_set, attr), type=True)
                    ))

                for member in cmds.ls(
                        cmds.sets(obj_set, query=True), long=True):
                    member_data = self.collect_member_data(member,
                                                           instance_lookup)
                    if not member_data:
                        continue

                    # Add information of the node to the members list
                    sets[obj_set]["members"].append(member_data)

            # Get all nodes of the current objectSet (shadingEngine)
            for member in cmds.ls(cmds.sets(obj_set, query=True), long=True):
                member_data = self.collect_member_data(member,
                                                       instance_lookup)
                if not member_data:
                    continue

                # Add information of the node to the members list
                sets[obj_set]["members"].append(member_data)

            # Remove sets that didn't have any members assigned in the end
            # Thus the data will be limited to only what we need.
            self.log.info("obj_set {}".format(sets[obj_set]))
            if not sets[obj_set]["members"]:
                self.log.info(
                    "Removing redundant set information: {}".format(obj_set))
                sets.pop(obj_set, None)

        self.log.info("Gathering attribute changes to instance members..")
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
            "aiVolumeShader"]
        if look_sets:
            materials = []

            for look in look_sets:
                for at in shader_attrs:
                    try:
                        con = cmds.listConnections("{}.{}".format(look, at))
                    except ValueError:
                        # skip attributes that are invalid in current
                        # context. For example in the case where
                        # Arnold is not enabled.
                        continue
                    if con:
                        materials.extend(con)

            self.log.info("Found materials:\n{}".format(materials))

            self.log.info("Found the following sets:\n{}".format(look_sets))
            # Get the entire node chain of the look sets
            # history = cmds.listHistory(look_sets)
            history = []
            for material in materials:
                history.extend(cmds.listHistory(material))

            # handle VrayPluginNodeMtl node - see #1397
            vray_plugin_nodes = cmds.ls(
                history, type="VRayPluginNodeMtl", long=True)
            for vray_node in vray_plugin_nodes:
                history.extend(cmds.listHistory(vray_node))

            # handling render attribute sets
            render_set_types = [
                "VRayDisplacement",
                "VRayLightMesh",
                "VRayObjectProperties",
                "RedshiftObjectId",
                "RedshiftMeshParameters",
            ]
            render_sets = cmds.ls(look_sets, type=render_set_types)
            if render_sets:
                history.extend(
                    cmds.listHistory(render_sets,
                                     future=False,
                                     pruneDagObjects=True)
                    or []
                )

            files = cmds.ls(history, type="file", long=True)
            files.extend(cmds.ls(history, type="aiImage", long=True))
            files.extend(cmds.ls(history, type="RedshiftNormalMap", long=True))

        self.log.info("Collected file nodes:\n{}".format(files))
        # Collect textures if any file nodes are found
        instance.data["resources"] = []
        for n in files:
            instance.data["resources"].append(self.collect_resource(n))

        self.log.info("Collected resources: {}".format(instance.data["resources"]))

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

        self.log.info("Collected look for %s" % instance)

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

            self.log.info(
                "Node \"{0}\" attributes: {1}".format(node, node_attrs)
            )

            # Only include if there are any properties we care about
            if not node_attrs:
                continue

            node_attributes = {}
            for attr in node_attrs:
                if not cmds.attributeQuery(attr, node=node, exists=True):
                    continue
                attribute = "{}.{}".format(node, attr)
                if cmds.getAttr(attribute, type=True) == "message":
                    continue
                node_attributes[attr] = cmds.getAttr(attribute)

            attributes.append({"name": node,
                               "uuid": lib.get_id(node),
                               "attributes": node_attributes})

        return attributes

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
            computed_attribute = "{}.computedFileTextureNamePattern".format(node)
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
