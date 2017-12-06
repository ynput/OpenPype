import os
import json
import re
import glob

from maya import cmds

from avalon import api
from avalon.maya import lib as avalon_lib, pipeline
from colorbleed.maya import lib


class YetiCacheLoader(api.Loader):

    families = ["colorbleed.yeticache", "colorbleed.yetiRig"]
    representations = ["fur"]

    label = "Load Yeti Cache"
    order = -9
    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, data=None):

        # Build namespace
        asset = context["asset"]
        if namespace is None:
            namespace = self.create_namespace(asset["name"])

        # Ensure Yeti is loaded
        if not cmds.pluginInfo("pgYetiMaya", query=True, loaded=True):
            cmds.loadPlugin("pgYetiMaya", quiet=True)

        # Get JSON
        fname, ext = os.path.splitext(self.fname)
        settings_fname = "{}.fursettings".format(fname)
        with open(settings_fname, "r") as fp:
            fursettings = json.load(fp)

        # Check if resources map exists
        # Get node name from JSON
        if "nodes" not in fursettings:
            raise RuntimeError("Encountered invalid data, expect 'nodes' in "
                               "fursettings.")

        node_data = fursettings["nodes"]
        nodes = self.create_nodes(namespace, node_data)

        group_name = "{}:{}".format(namespace, asset["name"])
        group_node = cmds.group(nodes, name=group_name)

        nodes.append(group_node)

        self[:] = nodes

        return pipeline.containerise(name=name,
                                     namespace=namespace,
                                     nodes=nodes,
                                     context=context,
                                     loader=self.__class__.__name__)

    def remove(self, container):

        from maya import cmds

        namespace = container["namespace"]
        container_name = container["objectName"]

        self.log.info("Removing '%s' from Maya.." % container["name"])

        container_content = cmds.sets(container_name, query=True)
        nodes = cmds.ls(container_content, long=True)

        nodes.append(container_name)

        try:
            cmds.delete(nodes)
        except ValueError:
            # Already implicitly deleted by Maya upon removing reference
            pass

        cmds.namespace(removeNamespace=namespace, deleteNamespaceContent=True)

    def update(self, container, representation):

        path = api.get_representation_path(representation)
        namespace = "{}:".format(container["namespace"])
        members = cmds.sets(container['objectName'], query=True)
        yeti_node = cmds.ls(members, type="pgYetiMaya")

        # TODO: Count the amount of nodes cached
        # To ensure new nodes get created or old nodes get destroyed

        for node in yeti_node:
            # Remove local given namespace
            node_name = node.split(namespace, 1)[-1]
            node_name = node_name.replace(":", "_")

            # Check if the node has a cache
            tmp_cache = os.path.join(path, "{}.%04d.fur".format(node_name))
            fpath = self.validate_cache(os.path.normpath(tmp_cache))

            # Update the attribute
            cmds.setAttr("{}.cacheFileName".format(node), fpath, type="string")

        # Update the container
        cmds.setAttr("{}.representation".format(container["objectName"]),
                     str(representation["_id"]),
                     type="string")

    # helper functions

    def create_namespace(self, asset):
        """Create a unique namespace
        Args:
            asset (dict): asset information

        """

        asset_name = "{}_".format(asset)
        prefix = "_" if asset_name[0].isdigit()else ""
        namespace = avalon_lib.unique_namespace(asset_name,
                                                prefix=prefix,
                                                suffix="_")

        return namespace

    def validate_cache(self, filename, pattern="%04d"):
        """Check if the cache has more than 1 frame

        All caches with more than 1 frame need to be called with `%04d`
        If the cache has only one frame we return that file name as we assume
        it is a snapshot.
        """

        glob_pattern = filename.replace(pattern, "*")

        escaped = re.escape(filename)
        re_pattern = escaped.replace(pattern, "-?[0-9]+")

        files = glob.glob(glob_pattern)
        files = [str(f) for f in files if re.match(re_pattern, f)]

        if len(files) == 1:
            return files[0]
        elif len(files) == 0:
            self.log.error("Could not find cache files for '%s'" % filename)

        return filename

    def create_nodes(self, namespace, settings):

        # Get node name from JSON
        nodes = []
        for node_settings in settings:

            # Create transform node
            transform = node_settings["transform"]
            transform_name = "{}:{}".format(namespace, transform["name"])
            transform_node = cmds.createNode("transform", name=transform_name)

            lib.set_id(transform_node, transform["cbId"])

            # Create pgYetiMaya node
            original_node = node_settings["name"]
            node_name = "{}:{}".format(namespace, original_node)
            yeti_node = cmds.createNode("pgYetiMaya",
                                        name=node_name,
                                        parent=transform_node)

            lib.set_id(yeti_node, node_settings["cbId"])

            nodes.append(transform_node)
            nodes.append(yeti_node)

            # Apply attributes to pgYetiMaya node
            kwargs = {}
            for attr, value in node_settings["attrs"].items():
                attribute = "%s.%s" % (yeti_node, attr)
                if isinstance(value, (str, unicode)):
                    cmds.setAttr(attribute, value, type="string")
                    continue
                cmds.setAttr(attribute, value, **kwargs)

            # Ensure the node has no namespace identifiers
            node_name = original_node.replace(":", "_")

            # Create full cache path
            cache = os.path.join(self.fname, "{}.%04d.fur".format(node_name))
            cache = os.path.normpath(cache)
            cache_fname = self.validate_cache(cache)
            cache_path = os.path.join(self.fname, cache_fname)

            # Preset the viewport density
            cmds.setAttr("%s.viewportDensity" % yeti_node, 0.1)

            # Add filename to `cacheFileName` attribute
            cmds.setAttr("%s.cacheFileName" % yeti_node,
                         cache_path,
                         type="string")

            # Set verbosity for debug purposes
            cmds.setAttr("%s.verbosity" % yeti_node, 2)

            # Enable the cache by setting the file mode
            cmds.setAttr("%s.fileMode" % yeti_node, 1)

            # Connect to the time node
            cmds.connectAttr("time1.outTime", "%s.currentTime" % yeti_node)

            nodes.append(yeti_node)
            nodes.append(transform_node)

        return nodes
