from pyblish import api

class CollectClipSubsets(api.InstancePlugin):
    """Collect Subsets from selected Clips, Tags, Preset."""

    order = api.CollectorOrder + 0.103
    label = "Collect Remove Clip Instaces"
    hosts = ["nukestudio"]
    families = ['clip']

    def process(self, instance):
        context = instance.context

        # removing original instance
        self.log.info("Removing instance.name: `{}`".format(instance.data["name"]))

        context.remove(instance)
