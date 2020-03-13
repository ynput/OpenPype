from pyblish import api


class CollectInstanceVersion(api.InstancePlugin):
    """ Collecting versions of Hiero project into instances

    If activated then any subset version is created in
    version of the actual project.
    """

    order = api.CollectorOrder + 0.011
    label = "Collect Instance Version"

    def process(self, instance):
        version = instance.context.data.get("version", "001")
        instance.data.update({
            "version": int(version)
        })
