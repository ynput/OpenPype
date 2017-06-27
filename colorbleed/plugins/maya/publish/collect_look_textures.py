from maya import cmds

import pyblish.api

import cb.utils.maya.shaders as shader

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

    order = pyblish.api.CollectorOrder + 0.498
    label = 'Textures'
    families = ["colorbleed.look"]
    actions = [SelectTextureNodesAction]

    def process(self, instance):

        verbose = instance.data.get("verbose", False)

        # Get textures from sets
        sets = instance.data["lookSets"]
        if not sets:
            raise RuntimeError("No look sets found for the nodes in the "
                               "instance. %s" % sets)

        # Get the file nodes
        history = cmds.listHistory(sets) or []
        files = cmds.ls(history, type="file")
        files = list(set(files))

        resources = instance.data.get("resources", [])
        for node in files:
            resource = self.collect_resources(node, verbose)
            if not resource:
                continue
            resources.append(resource)

        # Store resources
        instance.data['resources'] = resources

    def collect_resources(self, node, verbose=False):
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

        files = shader.get_file_node_files(node)
        if not files:
            self.log.error("File node does not have a texture set: "
                           "{0}".format(node))
            return

        # Define the resource
        resource = {"tags": TAGS[:],
                    "node": node,
                    "attribute": attribute,
                    "source": source,  # required for resources
                    "files": files,  # required for resources
                    "subfolder": "textures"  # optional for resources
                    }

        return resource
