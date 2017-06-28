from maya import cmds

from cb.utils.maya import context
import cbra.utils.maya.node_uuid as id_utils
import pyblish.api


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

    # Ignore specifically named sets (check with endswith)
    IGNORE = ["out_SET", "controls_SET", "_INST"]

    def process(self, instance):
        """Collect the Look in the instance with the correct layer settings"""

        layer = instance.data.get("renderlayer", "defaultRenderLayer")
        with context.renderlayer(layer):
            self.log.info("Checking out layer: {0}".format(layer))
            self.collect(instance)

    def collect(self, instance):

        # Whether to log information verbosely
        verbose = instance.data.get("verbose", False)

        self.log.info("Looking for look associations "
                      "for %s" % instance.data['name'])

        # Discover related object sets
        self.log.info("Gathering sets..")
        self.gather_sets(instance)

        # Lookup with absolute names (from root namespace)
        instance_lookup = set([str(x) for x in cmds.ls(instance,
                                                       long=True,
                                                       absoluteName=True)])

        self.log.info("Gathering set relations..")
        sets = self.gather_sets(instance)
        for objset in sets:

            self.log.debug("From %s.." % objset)
            content = cmds.sets(objset, query=True)
            objset_members = sets[objset]["members"]
            for member in cmds.ls(content, long=True, absoluteName=True):
                member_data = self.collect_member_data(member,
                                                       objset_members,
                                                       instance_lookup,
                                                       verbose)
                if not member_data:
                    continue

                sets[objset]["members"].append(member_data)

        # Remove sets that didn't have any members assigned in the end
        sets = self.clean_sets(sets)
        # Member attributes (shapes + transforms)

        self.log.info("Gathering attribute changes to instance members..")

        attributes = self.collect_attributes_changes(instance)
        looksets = cmds.ls(sets.keys(), absoluteName=True, long=True)

        # Store data on the instance
        instance.data["lookData"] = {"attributes": attributes,
                                     "relationships": sets.values(),
                                     "sets": looksets}

        # Log a warning when no relevant sets were retrieved for the look.
        if not instance.data["lookData"]["sets"]:
            self.log.warning("No sets found for the nodes in the instance: "
                             "%s" % instance[:])

        self.log.info("Collected look for %s" % instance)

    def gather_sets(self, instance):

        # Get view sets (so we can ignore those sets later)
        sets = dict()
        view_sets = set()
        model_panels = cmds.getPanel(type="modelPanel")
        for panel in model_panels:
            view_set = cmds.modelEditor(panel, query=True, viewObjects=True)
            if view_set:
                view_sets.add(view_set)

        for node in instance:
            node_sets = self.filter_sets(node, view_sets)
            if not node_sets:
                continue

            for objset in node_sets:
                if objset in sets:
                    continue
                sets[objset] = {"name": objset,
                                "uuid": id_utils.get_id(objset),
                                "members": list()}
        return sets

    def filter_sets(self, node, view_sets):

        node_sets = cmds.listSets(object=node, extendToShape=False) or []
        if not node_sets:
            return

        # Exclude deformer sets
        deformer_sets = cmds.listSets(object=node,
                                      extendToShape=False,
                                      type=2) or []
        deformer_sets = set(deformer_sets)  # optimize lookup
        sets = [s for s in node_sets if s not in deformer_sets]

        # Ignore specifically named sets
        sets = [s for s in sets if not any(s.endswith(x) for x in self.IGNORE)]

        # Ignore viewport filter view sets (from isolate select and
        # viewports)
        sets = [s for s in sets if s not in view_sets]

        self.log.info("Found sets {0} for {1}".format(node_sets, node))

        return sets

    def clean_sets(self, sets):

        for objset, data in sets.items():
            if not data['members']:
                self.log.debug("Removing redundant set "
                               "information: %s" % objset)
                sets.pop(objset)

        return sets

    def collect_member_data(self, member, objset_members, instance_members,
                            verbose=False):
        """Get all information of the node
        Args:
            member (str): the name of the node to check
            objset_members (list): the objectSet members
            instance_members (set): the collected instance members
            verbose (bool): get debug information

        Returns:
            dict

        """

        node, components = (member.rsplit(".", 1) + [None])[:2]

        # Only include valid members of the instance
        if node not in instance_members:
            if verbose:
                self.log.info("Skipping member %s" % member)
            return

        if member in [m["name"] for m in objset_members]:
            return

        if verbose:
            self.log.debug("Such as %s.." % member)

        member_data = {"name": node, "uuid": id_utils.get_id(node)}

        # Include components information when components are assigned
        if components:
            member_data["components"] = components

        return member_data

    def collect_attributes_changes(self, instance):

        attributes = []
        for node in instance:

            # Collect changes to "custom" attributes
            node_attrs = get_look_attrs(node)

            # Only include if there are any properties we care about
            if not node_attrs:
                continue

            node_attributes = {}
            for attr in node_attrs:
                attribute = "{}.{}".format(node, attr)
                node_attributes[attr] = cmds.getAttr(attribute)

            data = {"name": node,
                    "uuid": id_utils.get_id(node),
                    "attributes": node_attributes}

            attributes.append(data)

        return attributes
