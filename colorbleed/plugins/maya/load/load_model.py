import maya.cmds as cmds

from avalon import api
import avalon.maya


class ModelLoader(api.Loader):
    """Load the model"""

    families = ["colorbleed.model"]
    representations = ["ma"]

    label = "Reference Model"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process(self, name, namespace, context, data):

        # Create a readable namespace
        # Namespace should contain asset name and counter
        # TEST_001{_descriptor} where `descriptor` can be `_abc` for example
        assetname = "{}_".format(namespace.split("_")[0])
        namespace = avalon.maya.unique_namespace(assetname, format="%03d")

        with avalon.maya.maintained_selection():
            nodes = cmds.file(self.fname,
                              namespace=namespace,
                              reference=True,
                              returnNewNodes=True,
                              groupReference=True,
                              groupName="{}:{}".format(namespace, name))

        self[:] = nodes


class ModelGPUCacheLoader(api.Loader):
    """Import a GPU Cache"""

    families = ["colorbleed.model"]
    representations = ["abc"]

    label = "Import GPU Cache"
    order = -1
    icon = "download"

    def process(self, name, namespace, context, data):

        # todo: This will likely not be entirely safe with "containerize"
        # also this cannot work in the manager because it only works
        # on references at the moment!
        # especially in cases of duplicating the gpu cache node this will
        # mess up the "containered" workflow in the avalon core for maya
        print("WARNING: Importing gpuCaches isn't fully tested yet")

        path = self.fname

        cmds.loadPlugin("gpuCache", quiet=True)

        # Create transform with shape
        node_name = "{0}Shape".format(name)
        transform = cmds.createNode("transform", name=name)
        cache = cmds.createNode("gpuCache", parent=transform, name=node_name)

        # Set the cache filepath
        cmds.setAttr('{}.cacheFileName'.format(cache), path, type="string")
        cmds.setAttr('{}.cacheGeomPath'.format(cache), "|", type="string")  # root

        # Select the transform
        cmds.select(transform, r=1)

        # Store the created nodes
        self[:] = [transform, cache]
