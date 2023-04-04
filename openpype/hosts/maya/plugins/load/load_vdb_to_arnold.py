import os

from openpype.settings import get_project_settings
from openpype.pipeline import (
    load,
    get_representation_path
)
# TODO aiVolume doesn't automatically set velocity fps correctly, set manual?


class LoadVDBtoArnold(load.LoaderPlugin):
    """Load OpenVDB for Arnold in aiVolume"""

    families = ["vdbcache"]
    representations = ["vdb"]

    label = "Load VDB to Arnold"
    icon = "cloud"
    color = "orange"

    def load(self, context, name, namespace, data):

        from maya import cmds
        from openpype.hosts.maya.api.pipeline import containerise
        from openpype.hosts.maya.api.lib import unique_namespace

        try:
            family = context["representation"]["context"]["family"]
        except ValueError:
            family = "vdbcache"

        # Check if the plugin for arnold is available on the pc
        try:
            cmds.loadPlugin("mtoa", quiet=True)
        except Exception as exc:
            self.log.error("Encountered exception:\n%s" % exc)
            return

        asset = context['asset']
        asset_name = asset["name"]
        namespace = namespace or unique_namespace(
            asset_name + "_",
            prefix="_" if asset_name[0].isdigit() else "",
            suffix="_",
        )

        # Root group
        label = "{}:{}".format(namespace, name)
        root = cmds.group(name=label, empty=True)

        project_name = context["project"]["name"]
        settings = get_project_settings(project_name)
        colors = settings['maya']['load']['colors']

        c = colors.get(family)
        if c is not None:
            cmds.setAttr(root + ".useOutlinerColor", 1)
            cmds.setAttr(root + ".outlinerColor",
                         (float(c[0]) / 255),
                         (float(c[1]) / 255),
                         (float(c[2]) / 255)
                         )

        # Create VRayVolumeGrid
        grid_node = cmds.createNode("aiVolume",
                                    name="{}Shape".format(root),
                                    parent=root)

        path = self.filepath_from_context(context)
        self._set_path(grid_node,
                       path=path,
                       representation=context["representation"])

        # Lock the shape node so the user can't delete the transform/shape
        # as if it was referenced
        cmds.lockNode(grid_node, lock=True)

        nodes = [root, grid_node]
        self[:] = nodes

        return containerise(
            name=name,
            namespace=namespace,
            nodes=nodes,
            context=context,
            loader=self.__class__.__name__)

    def update(self, container, representation):

        from maya import cmds

        path = get_representation_path(representation)

        # Find VRayVolumeGrid
        members = cmds.sets(container['objectName'], query=True)
        grid_nodes = cmds.ls(members, type="aiVolume", long=True)
        assert len(grid_nodes) == 1, "This is a bug"

        # Update the VRayVolumeGrid
        self._set_path(grid_nodes[0], path=path, representation=representation)

        # Update container representation
        cmds.setAttr(container["objectName"] + ".representation",
                     str(representation["_id"]),
                     type="string")

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):

        from maya import cmds

        # Get all members of the avalon container, ensure they are unlocked
        # and delete everything
        members = cmds.sets(container['objectName'], query=True)
        cmds.lockNode(members, lock=False)
        cmds.delete([container['objectName']] + members)

        # Clean up the namespace
        try:
            cmds.namespace(removeNamespace=container['namespace'],
                           deleteNamespaceContent=True)
        except RuntimeError:
            pass

    @staticmethod
    def _set_path(grid_node,
                  path,
                  representation):
        """Apply the settings for the VDB path to the aiVolume node"""
        from maya import cmds

        if not os.path.exists(path):
            raise RuntimeError("Path does not exist: %s" % path)

        is_sequence = bool(representation["context"].get("frame"))
        cmds.setAttr(grid_node + ".useFrameExtension", is_sequence)

        # Set file path
        cmds.setAttr(grid_node + ".filename", path, type="string")
