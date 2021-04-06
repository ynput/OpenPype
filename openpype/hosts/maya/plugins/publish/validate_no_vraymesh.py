import pyblish.api
from maya import cmds


class ValidateNoVRayMesh(pyblish.api.InstancePlugin):
    """Validate there are no VRayMesh objects in the instance"""

    order = pyblish.api.ValidatorOrder
    label = 'No V-Ray Proxies (VRayMesh)'
    families = ["pointcache"]

    def process(self, instance):

        shapes = cmds.ls(instance,
                         shapes=True,
                         type="mesh")

        inputs = cmds.listConnections(shapes,
                                      destination=False,
                                      source=True) or []
        vray_meshes = cmds.ls(inputs, type='VRayMesh')
        if vray_meshes:
            raise RuntimeError("Meshes that are VRayMeshes shouldn't "
                               "be pointcached: {0}".format(vray_meshes))
