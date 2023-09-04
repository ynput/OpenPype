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
            layer = instance.data["renderlayer"]

        cameras = cmds.ls(type="camera", long=True)
        renderable = [cam for cam in cameras if
                      get_attr_in_layer("{}.renderable".format(cam), layer)]

        self.log.debug("Found %s renderable cameras: %s",
                       len(renderable), ", ".join(renderable))

        instance.data["cameras"] = renderable
