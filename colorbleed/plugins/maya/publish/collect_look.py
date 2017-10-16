from maya import cmds
import pyblish.api
import colorbleed.maya.lib as lib
from cb.utils.maya import context, shaders

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

    result = cmds.listAttr(node, userDefined=True,
                           changedSinceFileOpen=True) or []

    # For shapes allow render stat changes
    if cmds.objectType(node, isAType="shape"):
        attrs = cmds.listAttr(node, changedSinceFileOpen=True) or []
        valid = [attr for attr in attrs if attr in SHAPE_ATTRS]
        result.extend(valid)

    if "cbId" in result:
        result.remove("cbId")

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
        lookAttribtutes (list): Nodes in instance with their altered attributes
        lookSetRelations (list): Sets and their memberships
        lookSets (list): List of set names included in the look

    """

    order = pyblish.api.CollectorOrder + 0.4
    families = ["colorbleed.look"]
    label = "Collect Look"
    hosts = ["maya"]

    def process(self, instance):
        """Collect the Look in the instance with the correct layer settings"""

        with context.renderlayer(instance.data["renderlayer"]):
            self.collect(instance)

    def collect(self, instance):

        self.log.info("Looking for look associations "
                      "for %s" % instance.data['name'])

        # Discover related object sets
        self.log.info("Gathering sets..")
        sets = self.gather_sets(instance)

        # Lookup with absolute names (from root namespace)
        instance_lookup = set(cmds.ls(instance, long=True))

        self.log.info("Gathering set relations..")
        for objset in sets:
            self.log.debug("From %s.." % objset)
            objset_members = sets[objset]["members"]

            # Get all nodes of the current objectSet
            for member in cmds.ls(cmds.sets(objset, query=True), long=True):
                member_data = self.collect_member_data(member,
                                                       objset_members,
                                                       instance_lookup)
                if not member_data:
                    continue

                # Add information of the node to the members list
                sets[objset]["members"].append(member_data)

            # Remove sets that didn't have any members assigned in the end
            # Thus the data will be limited to only what we need.
            if not sets[objset]["members"]:
                self.log.info("Removing redundant set information: "
                              "%s" % objset)
                sets.pop(objset)

        self.log.info("Gathering attribute changes to instance members..")

        attributes = self.collect_attributes_changed(instance)
        looksets = cmds.ls(sets.keys(), long=True)

        self.log.info("Found the following sets:\n{}".format(looksets))

        # Store data on the instance
        instance.data["lookData"] = {"attributes": attributes,
                                     "relationships": sets}

        # Collect file nodes used by shading engines (if we have any)
        files = list()
        if looksets:
            # Get the entire node chain of the look sets
            history = cmds.listHistory(looksets)
            files = cmds.ls(history, type="file", long=True)

        # Collect textures
        instance.data["resources"] = [self.collect_resource(n) for n in files]

        # Log a warning when no relevant sets were retrieved for the look.
        if not instance.data["lookData"]["relationships"]:
            self.log.warning("No sets found for the nodes in the instance: "
                             "%s" % instance[:])

        self.log.info("Collected look for %s" % instance)

    def gather_sets(self, instance):
        """Gather all objectSets which are of importance for publishing

        It checks if all nodes in the instance are related to any objectSet
        which need to be

        Args:
            instance (list): all nodes to be published

        Returns:
            dict
        """

        sets = dict()
        for node in instance:
            related_sets = lib.get_related_sets(node)
            if not related_sets:
                continue

            for objset in related_sets:
                if objset in sets:
                    continue

                sets[objset] = {"uuid": lib.get_id(objset), "members": list()}

        return sets

    def collect_member_data(self, member, objset_members, instance_members):
        """Get all information of the node
        Args:
            member (str): the name of the node to check
            objset_members (list): the objectSet members
            instance_members (set): the collected instance members

        Returns:
            dict

        """

        node, components = (member.rsplit(".", 1) + [None])[:2]

        # Only include valid members of the instance
        if node not in instance_members:
            # Skip nodes which are not in the instance members
            return

        if member in [m["name"] for m in objset_members]:
            return

        if not cmds.attributeQuery("cbId", node=node, exists=True):
            self.log.error("Node '{}' has no attribute 'cbId'".format(node))
            return

        return {"name": node, "uuid": lib.get_id(node)}

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

            node_attributes = {}
            for attr in node_attrs:
                if not cmds.attributeQuery(attr, node=node, exists=True):
                    continue
                attribute = "{}.{}".format(node, attr)
                node_attributes[attr] = cmds.getAttr(attribute)

            attributes.append({"name": node,
                               "uuid": lib.get_id(node),
                               "attributes": node_attributes})

        return attributes

    def collect_resource(self, node, verbose=False):
        """Collect the link to the file(s) used (resource)
        Args:
            node (str): name of the node
            verbose (bool): enable debug information

        Returns:
            dict
        """

        attribute = "{}.fileTextureName".format(node)
        source = cmds.getAttr(attribute)

        # Get the computed file path (e.g. the one with the <UDIM> pattern
        # in it) So we can reassign it this computed file path whenever
        # we need to.
        computed_attribute = "{}.computedFileTextureNamePattern".format(node)
        computed_source = cmds.getAttr(computed_attribute)
        if source != computed_source:
            if verbose:
                self.log.debug("File node computed pattern differs from "
                               "original pattern: {0} "
                               "({1} -> {2})".format(node,
                                                     source,
                                                     computed_source))

            # We replace backslashes with forward slashes because V-Ray
            # can't handle the UDIM files with the backslashes in the
            # paths as the computed patterns
            source = computed_source.replace("\\", "/")

        files = shaders.get_file_node_files(node)
        if len(files) == 0:
            self.log.error("No valid files found from node `%s`" % node)

        # Define the resource
        return {"node": node,
                "attribute": attribute,
                "source": source,  # required for resources
                "files": files}  # required for resources
