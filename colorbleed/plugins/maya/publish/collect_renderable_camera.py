import pyblish.api

from maya import cmds

from colorbleed.maya import lib


class CollectRenderableCamera(pyblish.api.InstancePlugin):
    """Collect the renderable camera(s) for the render layer"""

    order = pyblish.api.CollectorOrder + 0.01
    label = "Collect Renderable Camera(s)"
    hosts = ["maya"]
    families = ["colorbleed.vrayscene",
                "colorbleed.renderlayer"]

    def process(self, instance):
        layer = instance.data["setMembers"]

        cameras = cmds.ls(type="camera", long=True)
        with lib.renderlayer(layer):
            renderable = [c for c in cameras if
                          cmds.getAttr("%s.renderable" % c)]

        self.log.info("Found cameras %s" % len(renderable))

        instance.data.update({"cameras": renderable})
