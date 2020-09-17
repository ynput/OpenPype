from pyblish import api


class CollectShots(api.InstancePlugin):
    """Collect Shot from Clip."""

    # Run just before CollectClipSubsets
    order = api.CollectorOrder + 0.1021
    label = "Collect Shots"
    hosts = ["nukestudio"]
    families = ["clip"]

    def process(self, instance):
        self.log.debug(
            "Skipping \"{}\" because its not tagged with "
            "\"Hierarchy\"".format(instance))
        # Exclude non-tagged instances.
        tagged = False
        for tag in instance.data["tags"]:
            if tag["name"].lower() == "hierarchy":
                tagged = True

        if not tagged:
            self.log.debug(
                "Skipping \"{}\" because its not tagged with "
                "\"Hierarchy\"".format(instance)
            )
            return

        # Collect data.
        data = {}
        for key, value in instance.data.iteritems():
            data[key] = value

        data["family"] = "shot"
        data["families"] = []

        data["subset"] = data["family"] + "Main"

        data["name"] = data["subset"] + "_" + data["asset"]

        data["label"] = (
            "{} - {} - tasks: {} - assetbuilds: {} - comments: {}".format(
                data["asset"],
                data["subset"],
                data["tasks"],
                [x["name"] for x in data.get("assetbuilds", [])],
                len(data.get("comments", []))
            )
        )

        # Create instance.
        self.log.debug("Creating instance with: {}".format(data["name"]))
        instance.context.create_instance(**data)
