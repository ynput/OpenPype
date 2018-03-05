from avalon import api
import colorbleed.maya.plugin


class ModelLoader(colorbleed.maya.plugin.ReferenceLoader):
    """Load the model"""

    families = ["colorbleed.model"]
    representations = ["ma"]

    label = "Reference Model"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process_reference(self, context, name, namespace, data):

        import maya.cmds as cmds
        from avalon import maya

        with maya.maintained_selection():
            nodes = cmds.file(self.fname,
                              namespace=namespace,
                              reference=True,
                              returnNewNodes=True,
                              groupReference=True,
                              groupName="{}:{}".format(namespace, name))

        self[:] = nodes

        return nodes

    def switch(self, container, representation):
        self.update(container, representation)


class ImportModelLoader(api.Loader):
    """An ImportModelLoader for Maya

     This will implement the basic behavior for a loader to inherit from that
     will containerize content. The loader will not be able to use `update`
     but only `remove`. When calling the `update` the loader will return a
     "NotImplementedError".

     """

    families = ["colorbleed.model"]
    representations = ["ma"]

    label = "Import Model"
    order = 10
    icon = "arrow-circle-down"
    color = "white"

    def load(self, context, name=None, namespace=None, data=None):

        import maya.cmds as cmds

        from avalon import maya
        from avalon.maya import lib
        from avalon.maya.pipeline import containerise

        asset = context['asset']

        namespace = namespace or lib.unique_namespace(
            asset["name"] + "_",
            prefix="_" if asset["name"][0].isdigit() else "",
            suffix="_",
        )

        with maya.maintained_selection():
            nodes = cmds.file(self.fname,
                              i=True,
                              namespace=namespace,
                              returnNewNodes=True,
                              groupReference=True,
                              groupName="{}:{}".format(namespace, name))

        # Only containerize if any nodes were loaded by the Loader
        if not nodes:
            return

        self[:] = nodes

        return containerise(
            name=name,
            namespace=namespace,
            nodes=nodes,
            context=context,
            loader=self.__class__.__name__)

    def update(self, container, representation):
        from avalon.vendor.Qt import QtWidgets

        message = ("The content of this asset was imported. "
                   "We cannot update this because we will need"
                   " to keep insane amount of things in mind.\n"
                   "Please remove and reimport the asset."
                   "\n\nIf you really need to update a lot we "
                   "recommend referencing.")

        QtWidgets.QMessageBox.critical(None,
                                       "Can't update",
                                       message,
                                       QtWidgets.QMessageBox.Ok)

        return

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


class GpuCacheLoader(api.Loader):
    """Load model Alembic as gpuCache"""

    families = ["colorbleed.model"]
    representations = ["abc"]

    label = "Import Gpu Cache"
    order = -5
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, data):

        import maya.cmds as cmds
        import avalon.maya.lib as lib
        from avalon.maya.pipeline import containerise

        asset = context['asset']['name']
        namespace = namespace or lib.unique_namespace(
            asset + "_",
            prefix="_" if asset[0].isdigit() else "",
            suffix="_",
        )

        cmds.loadPlugin("gpuCache", quiet=True)

        # Root group
        label = "{}:{}".format(namespace, name)
        root = cmds.group(name=label, empty=True)

        # Create transform with shape
        transform_name = label + "_GPU"
        transform = cmds.createNode("transform", name=transform_name,
                                    parent=root)
        cache = cmds.createNode("gpuCache",
                                parent=transform,
                                name="{0}Shape".format(transform_name))

        # Set the cache filepath
        cmds.setAttr(cache + '.cacheFileName', self.fname, type="string")
        cmds.setAttr(cache + '.cacheGeomPath', "|", type="string")    # root

        # Lock parenting of the transform and cache
        cmds.lockNode([transform, cache], lock=True)

        nodes = [root, transform, cache]
        self[:] = nodes

        return containerise(
            name=name,
            namespace=namespace,
            nodes=nodes,
            context=context,
            loader=self.__class__.__name__)

    def update(self, container, representation):

        import maya.cmds as cmds

        path = api.get_representation_path(representation)

        # Update the cache
        members = cmds.sets(container['objectName'], query=True)
        caches = cmds.ls(members, type="gpuCache", long=True)

        assert len(caches) == 1, "This is a bug"

        for cache in caches:
            cmds.setAttr(cache + ".cacheFileName", path, type="string")

        cmds.setAttr(container["objectName"] + ".representation",
                     str(representation["_id"]),
                     type="string")

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
