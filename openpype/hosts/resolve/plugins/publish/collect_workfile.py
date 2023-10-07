import pyblish.api


class CollectWorkfile(pyblish.api.InstancePlugin):
    """Collect the current working file into context"""

    families = ["workfile"]
    label = "Collect Workfile"
    order = pyblish.api.CollectorOrder - 0.49

    def process(self, instance):
        # Backwards compatibility - workfile instances previously had 'item'
        # in Resolve.
        # TODO: Remove this if it is not needed
        instance.data["item"] = instance.context.data["activeProject"]
