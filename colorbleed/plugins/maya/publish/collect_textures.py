from maya import cmds

import pyblish.api
import cb.utils.maya.shaders as shaders

TAGS = ["maya", "attribute", "look"]
TAGS_LOOKUP = set(TAGS)


class SelectTextureNodesAction(pyblish.api.Action):
    """Select the nodes related to the collected file textures"""

    label = "Select texture nodes"
    on = "succeeded"  # This action is only available on a failed plug-in
    icon = "search"  # Icon from Awesome Icon

    def process(self, context, plugin):

        self.log.info("Finding textures..")

        # Get the errored instances
        instances = []
        for result in context.data["results"]:
            instance = result["instance"]
            if instance is None:
                continue

            instances.append(instance)

        # Apply pyblish.logic to get the instances for the plug-in
        instances = pyblish.api.instances_by_plugin(instances, plugin)

        # Get the texture nodes from the instances
        nodes = []
        for instance in instances:
            for resource in instance.data.get("resources", []):
                if self.is_texture_resource(resource):
                    node = resource['node']
                    nodes.append(node)

        # Ensure unique
        nodes = list(set(nodes))

        if nodes:
            self.log.info("Selecting texture nodes: %s" % ", ".join(nodes))
            cmds.select(nodes, r=True, noExpand=True)
        else:
            self.log.info("No texture nodes found.")
            cmds.select(deselect=True)

    def is_texture_resource(self, resource):
        """Return whether the resource is a texture"""

        tags = resource.get("tags", [])
        if not TAGS_LOOKUP.issubset(tags):
            return False

        if resource.get("subfolder", None) != "textures":
            return False

        if "node" not in resource:
            return False

        return True


class CollectLookTextures(pyblish.api.InstancePlugin):
    """Collect look textures

    Includes the link from source to destination.

    """

    order = pyblish.api.CollectorOrder + 0.35
    label = 'Collect Look Textures'
    families = ["colorbleed.texture"]
    actions = [SelectTextureNodesAction]

    IGNORE = ["out_SET", "controls_SET", "_INST"]

    def process(self, instance):

        verbose = instance.data.get("verbose", False)

        # Get all texture nodes from the shader networks
        sets = self.gather_sets(instance)
        instance_members = {str(i) for i in cmds.ls(instance, long=True,
                                                    absoluteName=True)}

        self.log.info("Gathering set relations..")
        for objset in sets:
            self.log.debug("From %s.." % objset)
            content = cmds.sets(objset, query=True)
            objset_members = sets[objset]["members"]
            for member in cmds.ls(content, long=True, absoluteName=True):
                member_data = self.collect_member_data(member,
                                                       objset_members,
                                                       instance_members,
                                                       verbose)
                if not member_data:
                    continue

        # Get the file nodes
        history = cmds.listHistory(sets.keys()) or []
        files = cmds.ls(history, type="file")
        files = list(set(files))

        resources = instance.data.get("resources", [])
        for node in files:
            resource = self.collect_resources(node, verbose)
            if not resource:
                continue
            resources.append(resource)

        instance.data['resources'] = resources

    def gather_sets(self, instance):
        """Gather all objectSets which are of importance for publishing

        It checks if all nodes in the instance are related to any objectSet
        which need to be

        Args:
            instance (list): all nodes to be published

        Returns:
            dict
        """

        # Get view sets (so we can ignore those sets later)
        sets = dict()
        view_sets = set()
        for panel in cmds.getPanel(type="modelPanel"):
            view_set = cmds.modelEditor(panel, query=True,
                                        viewObjects=True)
            if view_set:
                view_sets.add(view_set)

        for node in instance:
            related_sets = self.get_related_sets(node, view_sets)
            if not related_sets:
                continue

            for objset in related_sets:
                if objset in sets:
                    continue
                unique_id = cmds.getAttr("%s.cbId" % objset)
                sets[objset] = {"name": objset,
                                "uuid": unique_id,
                                "members": list()}
        return sets

    def collect_resources(self, node, verbose=False):
        """Collect the link to the file(s) used (resource)
        Args:
            node (str): name of the node
            verbose (bool): enable debug information

        Returns:
            dict
        """

        # assure node includes full path
        node = cmds.ls(node, long=True)[0]
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
        if not files:
            self.log.error("File node does not have a texture set: "
                           "{0}".format(node))
            return

        # Define the resource
        # todo:  find a way to generate the destination for the publisher
        resource = {"tags": TAGS[:],
                    "node": node,
                    "attribute": attribute,
                    "source": source,  # required for resources
                    "files": files}  # required for resources

        return resource

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

        member_data = {"name": node,
                       "uuid": cmds.getAttr("{}.cbId".format(node, ))}

        # Include components information when components are assigned
        if components:
            member_data["components"] = components

        return member_data

    def get_related_sets(self, node, view_sets):
        """Get the sets which do not belong to any specific group

        Filters out based on:
        - id attribute is NOT `pyblish.avalon.container`
        - shapes and deformer shapes (alembic creates meshShapeDeformed)
        - set name ends with any from a predefined list
        - set in not in viewport set (isolate selected for example)

        Args:
            node (str): name of the current not to check
        """

        ignored = ["pyblish.avalon.instance", "pyblish.avalon.container"]

        related_sets = cmds.listSets(object=node, extendToShape=False)
        if not related_sets:
            return []

        # Ignore containers
        sets = [s for s in related_sets if
                not cmds.attributeQuery("id", node=s, exists=True) or
                not cmds.getAttr("%s.id" % s) in ignored]

        # Exclude deformer sets
        # Autodesk documentation on listSets command:
        # type(uint) : Returns all sets in the scene of the given
        # >>> type:
        # >>> 1 - all rendering sets
        # >>> 2 - all deformer sets
        deformer_sets = cmds.listSets(object=node, extendToShape=False,
                                      type=2) or []
        deformer_sets = set(deformer_sets)  # optimize lookup
        sets = [s for s in sets if s not in deformer_sets]

        # Ignore specifically named sets
        sets = [s for s in sets if not any(s.endswith(x) for x in self.IGNORE)]

        # Ignore viewport filter view sets (from isolate select and
        # viewports)
        sets = [s for s in sets if s not in view_sets]

        self.log.info("Found sets %s for %s" % (related_sets, node))

        return sets