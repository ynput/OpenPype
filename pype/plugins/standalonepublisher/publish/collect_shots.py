from pyblish import api


class CollectShots(api.InstancePlugin):
    """Collect Shot from Clip."""

    # Run just before CollectClipSubsets
    order = api.CollectorOrder + 0.1021
    label = "Collect Shots"
    hosts = ["standalonepublisher"]
    families = ["clip"]

    def process(self, instance):

        # Collect data.
        data = {}
        for key, value in instance.data.items():
            data[key] = value

        data["family"] = "shot"
        data["families"] = []

        data["subset"] = data["family"] + "Main"

        data["name"] = data["subset"] + "_" + data["asset"]

        data["label"] = (
            "{} - {} - tasks:{}".format(
                data["asset"],
                data["subset"],
                data["tasks"]
            )
        )

        # Create instance.
        self.log.debug("Creating instance with: {}".format(data["name"]))
        instance.context.create_instance(**data)
