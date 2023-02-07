import os
import clique

import maya.cmds as cmds
import mtoa.ui.arnoldmenu

from openpype.settings import get_project_settings
from openpype.pipeline import (
    load,
    get_representation_path
)
from openpype.hosts.maya.api.lib import (
    unique_namespace, get_attribute_input, maintained_selection
)
from openpype.hosts.maya.api.pipeline import containerise


def is_sequence(files):
    sequence = False
    collections, remainder = clique.assemble(files)
    if collections:
        sequence = True

    return sequence


class ArnoldStandinLoader(load.LoaderPlugin):
    """Load file as Arnold standin"""

    families = ["ass"]
    representations = ["ass"]

    label = "Load file as Arnold standin"
    order = -5
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, options):
        version = context['version']
        version_data = version.get("data", {})

        self.log.info("version_data: {}\n".format(version_data))

        asset = context['asset']['name']
        namespace = namespace or unique_namespace(
            asset + "_",
            prefix="_" if asset[0].isdigit() else "",
            suffix="_",
        )

        # Root group
        label = "{}:{}".format(namespace, name)
        root = cmds.group(name=label, empty=True)

        # Set color.
        project_name = context["project"]["name"]
        settings = get_project_settings(project_name)
        colors = settings['maya']['load']['colors']
        color = colors.get('ass')
        if color is not None:
            cmds.setAttr(root + ".useOutlinerColor", True)
            cmds.setAttr(
                root + ".outlinerColor", color[0], color[1], color[2]
            )

        with maintained_selection():
            # Create transform with shape
            transform_name = label + "_standin"

            standinShape = mtoa.ui.arnoldmenu.createStandIn()
            standin = cmds.listRelatives(standinShape, parent=True)[0]
            standin = cmds.rename(standin, transform_name)
            standinShape = cmds.listRelatives(standin, shapes=True)[0]

            cmds.parent(standin, root)

            # Set the standin filepath
            dso_path, operator = self._setup_proxy(standinShape, self.fname)
            cmds.setAttr(standinShape + ".dso", dso_path, type="string")
            sequence = is_sequence(os.listdir(os.path.dirname(self.fname)))
            cmds.setAttr(standinShape + ".useFrameExtension", sequence)

        nodes = [root, standin, operator]
        self[:] = nodes

        return containerise(
            name=name,
            namespace=namespace,
            nodes=nodes,
            context=context,
            loader=self.__class__.__name__)

    def get_next_free_multi_index(self, attr_name):
        """Find the next unconnected multi index at the input attribute."""

        start_index = 0
        # Assume a max of 10 million connections
        while start_index < 10000000:
            connection_info = cmds.connectionInfo(
                "{}[{}]".format(attr_name, start_index),
                sourceFromDestination=True
            )
            if len(connection_info or []) == 0:
                return start_index
            start_index += 1

    def _setup_proxy(self, shape, path):
        basename_split = os.path.basename(path).split(".")
        proxy_basename = (
            basename_split[0] + "_proxy." + ".".join(basename_split[1:])
        )
        proxy_path = "/".join(
            [os.path.dirname(path), "resources", proxy_basename]
        )

        if not os.path.exists(proxy_path):
            self.log.error("Proxy files do not exist. Skipping proxy setup.")
            return path

        options_node = "defaultArnoldRenderOptions"
        merge_operator = get_attribute_input(options_node + ".operator")
        if merge_operator is None:
            merge_operator = cmds.createNode("aiMerge")
            cmds.connectAttr(
                merge_operator + ".message", options_node + ".operator"
            )

        merge_operator = merge_operator.split(".")[0]

        string_replace_operator = cmds.createNode("aiStringReplace")
        cmds.setAttr(
            string_replace_operator + ".selection",
            "*.(@node=='procedural')",
            type="string"
        )
        cmds.setAttr(
            string_replace_operator + ".match",
            "resources/" + proxy_basename,
            type="string"
        )
        cmds.setAttr(
            string_replace_operator + ".replace",
            os.path.basename(path),
            type="string"
        )

        cmds.connectAttr(
            string_replace_operator + ".out",
            "{}.inputs[{}]".format(
                merge_operator,
                self.get_next_free_multi_index(merge_operator + ".inputs")
            )
        )

        return proxy_path, string_replace_operator

    def update(self, container, representation):
        # Update the standin
        standins = list()
        members = cmds.sets(container['objectName'], query=True)
        for member in members:
            shapes = cmds.listRelatives(member, shapes=True)
            if not shapes:
                continue
            if cmds.nodeType(shapes[0]) == "aiStandIn":
                standins.append(shapes[0])

        path = get_representation_path(representation)
        sequence = is_sequence(os.listdir(os.path.dirname(path)))
        for standin in standins:
            cmds.setAttr(standin + ".dso", path, type="string")
            cmds.setAttr(standin + ".useFrameExtension", sequence)

        cmds.setAttr(
            container["objectName"] + ".representation",
            str(representation["_id"]),
            type="string"
        )

    def switch(self, container, representation):
        self.update(container, representation)

    def remove(self, container):
        import maya.cmds as cmds
        members = cmds.sets(container['objectName'], query=True)
        cmds.lockNode(members, lock=False)
        cmds.delete([container['objectName']] + members)

        # Clean up the namespace
        try:
            cmds.namespace(removeNamespace=container['namespace'],
                           deleteNamespaceContent=True)
        except RuntimeError:
            pass
