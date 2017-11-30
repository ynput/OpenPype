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
        # TODO: should be stored in fursettings
        image_search_path = ""
        version_folder = os.path.dirname(self.fname)
        resource_folder = os.path.join(version_folder, "resources")
        if os.path.exists(resource_folder):
            image_search_path = os.path.normpath(resource_folder)

        # Get node name from JSON
        nodes = []
        for node, settings in fursettings.items():

            # Create new pgYetiMaya node
            node_name = "{}:{}".format(namespace, node)
            yeti_node = cmds.createNode("pgYetiMaya", name=node_name)
            cmds.connectAttr("time1.outTime", "%s.currentTime" % yeti_node)

            # Apply colorbleed ID to node
            lib.set_id(node=yeti_node,
                       unique_id=settings["cbId"],
                       overwrite=True)
            settings.pop("cbId", None)

            # Apply settings
            for attr, value in settings.items():
                attribute = "%s.%s" % (yeti_node, attr)
                cmds.setAttr(attribute, value)

            # Ensure the node has no namespace identifiers
            node = node.replace(":", "_")

            # Create full cache path
            cache = os.path.join(self.fname, "{}.%04d.fur".format(node))
            cache_fname = self.validate_cache(cache)
            cache_path = os.path.join(self.fname, cache_fname)

            # Add filename to `cacheFileName` attribute, set to cache mode
            cmds.setAttr("%s.cacheFileName" % yeti_node,
                         cache_path,
                         type="string")

            cmds.setAttr("%s.fileMode" % yeti_node, 1)
            cmds.setAttr("%s.imageSearchPath" % yeti_node,
                         image_search_path,
                         type="string")

            cmds.setAttr("%s.verbosity" % yeti_node, 2)

            nodes.append(yeti_node)

        group_name = "{}:{}".format(namespace, asset["name"])
        group_node = cmds.group(nodes, name=group_name)
        all_nodes = cmds.listRelatives(group_node, children=True)
        all_nodes.append(group_node)

        self[:] = all_nodes

        return pipeline.containerise(name=name,
                                     namespace=namespace,
                                     nodes=all_nodes,
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
        members = cmds.sets(container['objectName'], query=True)
        all_members = cmds.listRelatives(members, ad=True)
        yeti_node = cmds.ls(all_members, type="pgYetiMaya", long=True)

        for node in yeti_node:
            node_name = node.split(":")[-1]
            tmp_cache = os.path.join(path, "{}.%04d.fur".format(node_name))
            fpath = self.validate_cache(os.path.normpath(tmp_cache))
            cmds.setAttr("{}.cacheFileName".format(node), fpath, type="string")

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

