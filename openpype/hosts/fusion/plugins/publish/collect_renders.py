import pyblish.api


class CollectFusionRenders(pyblish.api.InstancePlugin):
    """Collect current saver node's render Mode

    Options:
        local (Render locally)
        frames (Use existing frames)

    """

    order = pyblish.api.CollectorOrder + 0.4
    label = "Collect Renders"
    hosts = ["fusion"]
    families = ["render"]

    def process(self, instance):
        render_target = instance.data["render_target"]
        family = instance.data["family"]

        # add targeted family to families
        instance.data["families"].append(
            "{}.{}".format(family, render_target)
        )
