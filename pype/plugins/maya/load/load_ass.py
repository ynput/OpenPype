from avalon import api
import pype.maya.plugin
import os


class AssProxyLoader(pype.maya.plugin.ReferenceLoader):
    """Load the Proxy"""

    families = ["ass"]
    representations = ["ass"]

    label = "Reference .ASS standin with Proxy"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name, namespace, data):

        import maya.cmds as cmds
        from avalon import maya
        import pymel.core as pm

        with maya.maintained_selection():

            groupName = "{}:{}".format(namespace, name)
            path = self.fname
            proxyPath = os.path.splitext(path)[0] + ".ma"

            nodes = cmds.file(proxyPath,
                              namespace=namespace,
                              reference=True,
                              returnNewNodes=True,
                              groupReference=True,
                              groupName=groupName)

            cmds.makeIdentity(groupName, apply=False, rotate=True, translate=True, scale=True)

            # Set attributes
            proxyShape = pm.ls(nodes, type="mesh")[0]
            proxyShape = pm.ls(nodes, type="mesh")[0]

            proxyShape.aiTranslator.set('procedural')
            proxyShape.dso.set(path)
            proxyShape.aiOverrideShaders.set(0)


        self[:] = nodes

        return nodes

    def switch(self, container, representation):
        self.update(container, representation)


class AssStandinLoader(api.Loader):
    """Load .ASS file as standin"""

    families = ["ass"]
    representations = ["ass"]

    label = "Load .ASS file as standin"
    order = -5
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, data):

        import maya.cmds as cmds
        import avalon.maya.lib as lib
        from avalon.maya.pipeline import containerise
        import mtoa.ui.arnoldmenu
        import pymel.core as pm


        asset = context['asset']['name']
        namespace = namespace or lib.unique_namespace(
            asset + "_",
            prefix="_" if asset[0].isdigit() else "",
            suffix="_",
        )

        # cmds.loadPlugin("gpuCache", quiet=True)

        # Root group
        label = "{}:{}".format(namespace, name)
        root = pm.group(name=label, empty=True)

        # Create transform with shape
        transform_name = label + "_ASS"
        # transform = pm.createNode("transform", name=transform_name,
        #                             parent=root)

        standinShape = pm.PyNode(mtoa.ui.arnoldmenu.createStandIn())
        standin = standinShape.getParent()
        standin.rename(transform_name)

        pm.parent(standin, root)

        # Set the standin filepath
        standinShape.dso.set(self.fname)


        # Lock parenting of the transform and standin
        cmds.lockNode([root, standin], lock=True)

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

        path = api.get_representation_path(representation)

        # Update the standin
        members = pm.sets(container['objectName'], query=True)
        standins = pm.ls(members, type="AiStandIn", long=True)

        assert len(caches) == 1, "This is a bug"

        for standin in standins:
            standin.cacheFileName.set(path)

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
