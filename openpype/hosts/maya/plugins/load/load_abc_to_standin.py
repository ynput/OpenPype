import os
import clique

from openpype.pipeline import (
    load,
    get_representation_path
)
from openpype.settings import get_project_settings


class AlembicStandinLoader(load.LoaderPlugin):
    """Load Alembic as Arnold Standin"""

    families = ["model", "pointcache"]
    representations = ["abc"]

    label = "Import Alembic as Standin"
    order = -5
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, options):

        import maya.cmds as cmds
        import pymel.core as pm
        import mtoa.ui.arnoldmenu
        from openpype.hosts.maya.api.pipeline import containerise
        from openpype.hosts.maya.api.lib import unique_namespace

        version = context["version"]
        version_data = version.get("data", {})

        self.log.info("version_data: {}\n".format(version_data))

        frameStart = version_data.get("frameStart", None)

        asset = context["asset"]["name"]
        namespace = namespace or unique_namespace(
            asset + "_",
            prefix="_" if asset[0].isdigit() else "",
            suffix="_",
        )

        #Root group
        label = "{}:{}".format(namespace, name)
        root = pm.group(name=label, empty=True)

        settings = get_project_settings(os.environ['AVALON_PROJECT'])
        colors = settings["maya"]["load"]["colors"]

        c = colors.get('ass')
        if c is not None:
            cmds.setAttr(root + ".useOutlinerColor", 1)
            cmds.setAttr(root + ".outlinerColor",
                         c[0], c[1], c[2])

        transform_name = label + "_ABC"

        standinShape = pm.PyNode(mtoa.ui.arnoldmenu.createStandIn())
        standin = standinShape.getParent()
        standin.rename(transform_name)

        pm.parent(standin, root)

        # Set the standin filepath
        standinShape.dso.set(self.fname)
        if frameStart is not None:
            standinShape.useFrameExtension.set(1)

        nodes = [root, standin]
        self[:] = nodes

        return containerise(
            name=name,
            namespace=namespace,
            nodes=nodes,
            context=context,
            loader=self.__class__.__name__)

    def update(self, container, representation):

        import pymel.core as pm

        path = get_representation_path(representation)

        # Update the standin
        standins = list()
        members = pm.sets(container['objectName'], query=True)
        for member in members:
            shape = member.getShape()
            if (shape and shape.type() == "aiStandIn"):
                standins.append(shape)

        for standin in standins:
            standin.dso.set(path)
            standin.useFrameExtension.set(1)

        container = pm.PyNode(container["objectName"])
        container.representation.set(str(representation["_id"]))

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
