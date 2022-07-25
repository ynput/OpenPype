import pyblish.api

from maya import cmds

from openpype.hosts.maya.api.lib_rendersetup import get_attr_in_layer


class CollectRenderableCamera(pyblish.api.InstancePlugin):
    """Collect the renderable camera(s) for the render layer"""

    # Offset to be after renderlayer collection.
    order = pyblish.api.CollectorOrder + 0.02
    label = "Collect Renderable Camera(s)"
    hosts = ["maya"]
    families = ["vrayscene_layer",
                "renderlayer"]

    def process(self, instance):
        if "vrayscene_layer" in instance.data.get("families", []):
            layer = instance.data.get("layer")
        else:
            layer = instance.data["setMembers"]

        self.log.info("layer: {}".format(layer))
        cameras = cmds.ls(type="camera", long=True)
        renderable = [c for c in cameras if
                      get_attr_in_layer("%s.renderable" % c, layer)]

        self.log.info("Found cameras %s: %s" % (len(renderable), renderable))

        instance.data["cameras"] = renderable
