from maya import cmds

from avalon import api
from avalon import maya


class ModelLoader(api.Loader):
    """Load the model"""

    families = ["colorbleed.model"]
    representations = ["ma"]

    label = "Reference model"
    order = -10
    icon = "code-fork"
    color = "orange"

    def process(self, name, namespace, context, data):

        with maya.maintained_selection():
            nodes = cmds.file(
                self.fname,
                namespace=namespace,
                reference=True,
                returnNewNodes=True,
                groupReference=True,
                groupName="{}:{}".format(namespace, name)
            )

        # Assign default shader to meshes
        meshes = cmds.ls(nodes, type="mesh")
        cmds.sets(meshes, forceElement="initialShadingGroup")

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
        transform = cmds.createNode("transform",
                                    name=name)
        cache = cmds.createNode("gpuCache",
                                parent=transform,
                                name="{0}Shape".format(name))

        # Set the cache filepath
        cmds.setAttr(cache + '.cacheFileName', path, type="string")
        cmds.setAttr(cache + '.cacheGeomPath', "|", type="string")    # root

        # Select the transform
        cmds.select(transform, r=1)

        # Store the created nodes
        self[:] = [transform, cache]
