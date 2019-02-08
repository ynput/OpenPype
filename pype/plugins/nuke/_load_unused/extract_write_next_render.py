import pyblish.api


class WriteToRender(pyblish.api.InstancePlugin):
    """Swith Render knob on write instance to on,
    so next time publish will be set to render
    """

    order = pyblish.api.ExtractorOrder + 0.1
    label = "Write to render next"
    optional = True
    hosts = ["nuke", "nukeassist"]
    families = ["write"]

    def process(self, instance):
        return
        if [f for f in instance.data["families"]
                if ".frames" in f]:
            instance[0]["render"].setValue(True)
            self.log.info("Swith write node render to `on`")
        else:
            # swith to
            instance[0]["render"].setValue(False)
            self.log.info("Swith write node render to `Off`")
