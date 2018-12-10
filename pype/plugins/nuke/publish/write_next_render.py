import pyblish.api


class WriteToRender(pyblish.api.InstancePlugin):
    """Swith Render knob on write instance to on,
    so next time publish will be set to render
    """

    order = pyblish.api.IntegratorOrder + 11
    label = "Write to render next"
    optional = True
    hosts = ["nuke", "nukeassist"]
    families = ["render.frames", "still.frames", "prerender.frames"]

    def process(self, instance):
        instance[0]["render"].setValue(True)
        self.log.info("Swith write node render to `on`")
