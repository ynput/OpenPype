import os
import clique

import maya.cmds as cmds
import mtoa.ui.arnoldmenu

from openpype.settings import get_project_settings
from openpype.pipeline import (
    load,
    get_representation_path
)
from openpype.hosts.maya.api.lib import unique_namespace
from openpype.hosts.maya.api.pipeline import containerise


def is_sequence(files):
    sequence = False
    collections, remainder = clique.assemble(files)
    if collections:
        sequence = True

    return sequence


def set_color(node, context):
    project_name = context["project"]["name"]
    settings = get_project_settings(project_name)
    colors = settings['maya']['load']['colors']
    color = colors.get('ass')
    if color is not None:
        cmds.setAttr(node + ".useOutlinerColor", True)
        cmds.setAttr(
            node + ".outlinerColor", color[0], color[1], color[2]
        )


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

        set_color(root, context)

        # Create transform with shape
        transform_name = label + "_standin"

        standinShape = mtoa.ui.arnoldmenu.createStandIn()
        standin = cmds.listRelatives(standinShape, parent=True)[0]
        standin = cmds.rename(standin, transform_name)
        standinShape = cmds.listRelatives(standin, shapes=True)[0]

        cmds.parent(standin, root)

        # Set the standin filepath
        cmds.setAttr(standinShape + ".dso", self.fname, type="string")
        sequence = is_sequence(os.listdir(os.path.dirname(self.fname)))
        cmds.setAttr(standinShape + ".useFrameExtension", sequence)

        nodes = [root, standin]
        self[:] = nodes

        return containerise(
            name=name,
            namespace=namespace,
            nodes=nodes,
            context=context,
            loader=self.__class__.__name__)

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
