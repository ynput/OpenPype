import os
import json
import re
import glob
from collections import defaultdict
from pprint import pprint

from maya import cmds

from avalon import io
from openpype.api import get_project_settings
from openpype.pipeline import (
    load,
    get_representation_path
)
from openpype.hosts.maya.api import lib
from openpype.hosts.maya.api.pipeline import containerise


class YetiCacheLoader(load.LoaderPlugin):

    families = ["yeticache", "yetiRig"]
    representations = ["fur"]

    label = "Load Yeti Cache"
    order = -9
    icon = "code-fork"
    color = "orange"

    def load(self, context, name=None, namespace=None, data=None):

        try:
            family = context["representation"]["context"]["family"]
        except ValueError:
            family = "yeticache"

        # Build namespace
        asset = context["asset"]
        if namespace is None:
            namespace = self.create_namespace(asset["name"])

        # Ensure Yeti is loaded
        if not cmds.pluginInfo("pgYetiMaya", query=True, loaded=True):
            cmds.loadPlugin("pgYetiMaya", quiet=True)

        # Get JSON
        fbase = re.search(r'^(.+)\.(\d+|#+)\.fur', self.fname)
        if not fbase:
            raise RuntimeError('Cannot determine fursettings file path')
        settings_fname = "{}.fursettings".format(fbase.group(1))
        with open(settings_fname, "r") as fp:
            fursettings = json.load(fp)

        # Check if resources map exists
        # Get node name from JSON
        if "nodes" not in fursettings:
            raise RuntimeError("Encountered invalid data, expect 'nodes' in "
                               "fursettings.")

        node_data = fursettings["nodes"]
        nodes = self.create_nodes(namespace, node_data)

        group_name = "{}:{}".format(namespace, name)
        group_node = cmds.group(nodes, name=group_name)

        settings = get_project_settings(os.environ['AVALON_PROJECT'])
        colors = settings['maya']['load']['colors']

        c = colors.get(family)
        if c is not None:
            cmds.setAttr(group_name + ".useOutlinerColor", 1)
            cmds.setAttr(group_name + ".outlinerColor",
                (float(c[0])/255),
                (float(c[1])/255),
                (float(c[2])/255)
            )

        nodes.append(group_node)

        self[:] = nodes

        return containerise(
            name=name,
            namespace=namespace,
            nodes=nodes,
            context=context,
            loader=self.__class__.__name__
        )

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

        io.install()
        namespace = container["namespace"]
        container_node = container["objectName"]

        fur_settings = io.find_one(
            {"parent": representation["parent"], "name": "fursettings"}
        )

        pprint({"parent": representation["parent"], "name": "fursettings"})
        pprint(fur_settings)
        assert fur_settings is not None, (
            "cannot find fursettings representation"
        )

        settings_fname = get_representation_path(fur_settings)
        path = get_representation_path(representation)
        # Get all node data
        with open(settings_fname, "r") as fp:
            settings = json.load(fp)

        # Collect scene information of asset
        set_members = cmds.sets(container["objectName"], query=True)
        container_root = lib.get_container_transforms(container,
                                                      members=set_members,
                                                      root=True)
        scene_nodes = cmds.ls(set_members, type="pgYetiMaya", long=True)

        # Build lookup with cbId as keys
        scene_lookup = defaultdict(list)
        for node in scene_nodes:
            cb_id = lib.get_id(node)
            scene_lookup[cb_id].append(node)

        # Re-assemble metadata with cbId as keys
        meta_data_lookup = {n["cbId"]: n for n in settings["nodes"]}

        # Compare look ups and get the nodes which ar not relevant any more
        to_delete_lookup = {cb_id for cb_id in scene_lookup.keys() if
                            cb_id not in meta_data_lookup}
        if to_delete_lookup:

            # Get nodes and remove entry from lookup
            to_remove = []
            for _id in to_delete_lookup:
                # Get all related nodes
                shapes = scene_lookup[_id]
                # Get the parents of all shapes under the ID
                transforms = cmds.listRelatives(shapes,
                                                parent=True,
                                                fullPath=True) or []
                to_remove.extend(shapes + transforms)

                # Remove id from look uop
                scene_lookup.pop(_id, None)

            cmds.delete(to_remove)

        # replace frame in filename with %04d
        RE_frame = re.compile(r"(\d+)(\.fur)$")
        file_name = re.sub(RE_frame, r"%04d\g<2>", os.path.basename(path))
        for cb_id, data in meta_data_lookup.items():

            # Update cache file name
            data["attrs"]["cacheFileName"] = os.path.join(
                os.path.dirname(path), file_name)

            if cb_id not in scene_lookup:

                self.log.info("Creating new nodes ..")

                new_nodes = self.create_nodes(namespace, [data])
                cmds.sets(new_nodes, addElement=container_node)
                cmds.parent(new_nodes, container_root)

            else:
                # Update the matching nodes
                scene_nodes = scene_lookup[cb_id]
                lookup_result = meta_data_lookup[cb_id]["name"]

                # Remove namespace if any (e.g.: "character_01_:head_YNShape")
                node_name = lookup_result.rsplit(":", 1)[-1]

                for scene_node in scene_nodes:

                    # Get transform node, this makes renaming easier
                    transforms = cmds.listRelatives(scene_node,
                                                    parent=True,
                                                    fullPath=True) or []
                    assert len(transforms) == 1, "This is a bug!"

                    # Get scene node's namespace and rename the transform node
                    lead = scene_node.rsplit(":", 1)[0]
                    namespace = ":{}".format(lead.rsplit("|")[-1])

                    new_shape_name = "{}:{}".format(namespace, node_name)
                    new_trans_name = new_shape_name.rsplit("Shape", 1)[0]

                    transform_node = transforms[0]
                    cmds.rename(transform_node,
                                new_trans_name,
                                ignoreShape=False)

                    # Get the newly named shape node
                    yeti_nodes = cmds.listRelatives(new_trans_name,
                                                    children=True)
                    yeti_node = yeti_nodes[0]

                    for attr, value in data["attrs"].items():
                        # handle empty attribute strings. Those are reported
                        # as None, so their type is NoneType and this is not
                        # supported on attributes in Maya. We change it to
                        # empty string.
                        if value is None:
                            value = ""
                        lib.set_attribute(attr, value, yeti_node)

        cmds.setAttr("{}.representation".format(container_node),
                     str(representation["_id"]),
                     typ="string")

    def switch(self, container, representation):
        self.update(container, representation)

    # helper functions

    def create_namespace(self, asset):
        """Create a unique namespace
        Args:
            asset (dict): asset information

        """

        asset_name = "{}_".format(asset)
        prefix = "_" if asset_name[0].isdigit()else ""
        namespace = lib.unique_namespace(
            asset_name,
            prefix=prefix,
            suffix="_"
        )

        return namespace

    def validate_cache(self, filename, pattern="%04d"):
        """Check if the cache has more than 1 frame

        All caches with more than 1 frame need to be called with `%04d`
        If the cache has only one frame we return that file name as we assume
        it is a snapshot.

        Args:
            filename(str)
            pattern(str)

        Returns:
            str

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
        """Create nodes with the correct namespace and settings

        Args:
            namespace(str): namespace
            settings(list): list of dictionaries

        Returns:
             list

        """

        nodes = []
        for node_settings in settings:

            # Create pgYetiMaya node
            original_node = node_settings["name"]
            node_name = "{}:{}".format(namespace, original_node)
            yeti_node = cmds.createNode("pgYetiMaya", name=node_name)

            # Create transform node
            transform_node = node_name.rstrip("Shape")

            lib.set_id(transform_node, node_settings["transform"]["cbId"])
            lib.set_id(yeti_node, node_settings["cbId"])

            nodes.extend([transform_node, yeti_node])

            # Ensure the node has no namespace identifiers
            attributes = node_settings["attrs"]

            # Check if cache file name is stored

            # get number of # in path and convert it to C prinf format
            # like %04d expected by Yeti
            fbase = re.search(r'^(.+)\.(\d+|#+)\.fur', self.fname)
            if not fbase:
                raise RuntimeError('Cannot determine file path')
            padding = len(fbase.group(2))
            if "cacheFileName" not in attributes:
                cache = "{}.%0{}d.fur".format(fbase.group(1), padding)

                self.validate_cache(cache)
                attributes["cacheFileName"] = cache

            # Update attributes with requirements
            attributes.update({"viewportDensity": 0.1,
                               "verbosity": 2,
                               "fileMode": 1})

            # Apply attributes to pgYetiMaya node
            for attr, value in attributes.items():
                if value is None:
                    continue
                lib.set_attribute(attr, value, yeti_node)

            # Fix for : YETI-6
            # Fixes the render stats (this is literally taken from Perigrene's
            # ../scripts/pgYetiNode.mel script)
            cmds.setAttr("{}.visibleInReflections".format(yeti_node), True)
            cmds.setAttr("{}.visibleInRefractions".format(yeti_node), True)

            # Connect to the time node
            cmds.connectAttr("time1.outTime", "%s.currentTime" % yeti_node)

        return nodes
