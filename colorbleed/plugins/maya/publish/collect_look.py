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
                      "for {0}..".format(instance.data['label']))

        # Get view sets (so we can ignore those sets later)
        model_panels = cmds.getPanel(type="modelPanel")
        view_sets = set()

        for panel in model_panels:
            view_set = cmds.modelEditor(panel, query=True, viewObjects=True)
            if view_set:
                view_sets.add(view_set)

        # Discover related object sets
        self.log.info("Gathering sets..")
        sets = dict()
        for node in instance:

            node_sets = cmds.listSets(object=node, extendToShape=False) or []
            if verbose:
                self.log.info("Found raw sets "
                              "{0} for {1}".format(node_sets, node))

            if not node_sets:
                continue

            # Exclude deformer sets
            deformer_sets = cmds.listSets(object=node,
                                          extendToShape=False,
                                          type=2) or []
            deformer_sets = set(deformer_sets)  # optimize lookup
            node_sets = [s for s in node_sets if s not in deformer_sets]

            if verbose:
                self.log.debug("After filtering deformer sets "
                               "{0}".format(node_sets))

            # Ignore specifically named sets
            node_sets = [s for s in node_sets if
                         not any(s.endswith(x) for x in self.IGNORE)]

            if verbose:
                self.log.debug("After filtering ignored sets "
                               "{0}".format(node_sets))

            # Ignore viewport filter view sets (from isolate select and
            # viewports)
            node_sets = [s for s in node_sets if s not in view_sets]

            if verbose:
                self.log.debug("After filtering view sets %s" % node_sets)

            self.log.info("Found sets {0} for {1}".format(node_sets, node))

            for objset in node_sets:
                if objset not in sets:
                    sets[objset] = {"name": objset,
                                    "uuid": id_utils.get_id(objset),
                                    "members": list()}

        # Lookup with absolute names (from root namespace)
        instance_lookup = set([str(x) for x in cmds.ls(instance,
                                                       long=True,
                                                       absoluteName=True)])

        self.log.info("Gathering set relations..")
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
        for objset, data in sets.items():
            if not data['members']:
                self.log.debug("Removing redundant set "
                               "information: {0}".format(objset))
                sets.pop(objset)

        # Member attributes (shapes + transforms)

        self.log.info("Gathering attribute changes to instance members..")
        attrs = []
        for node in instance:

            # Collect changes to "custom" attributes
            node_attrs = get_look_attrs(node)

            # Only include if there are any properties we care about
            if not node_attrs:
                continue

            attributes = {}
            for attr in node_attrs:
                attribute = "{}.{}".format(node, attr)
                attributes[attr] = cmds.getAttr(attribute)

            # attributes = dict((attr, pm.getAttr("{}.{}".format(node, attr))
            #                    for attr in node_attrs))
            data = {"name": node,
                    "uuid": id_utils.get_id(node),
                    "attributes": attributes}

            attrs.append(data)

        # Store data on the instance
        instance.data["lookAttributes"] = attrs
        instance.data["lookSetRelations"] = sets.values()
        instance.data["lookSets"] = cmds.ls(sets.keys(),
                                            absoluteName=True,
                                            long=True)

        # Log a warning when no relevant sets were retrieved for the look.
        if not instance.data['lookSets']:
            self.log.warning("No sets found for the nodes in the instance: {0}".format(instance[:]))

        self.log.info("Collected look for %s" % instance)

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



