from pyblish import api
import os

class CollectAudio(api.InstancePlugin):
    """Collect audio from tags.

    Tag is expected to have metadata:
        {
            "family": "audio",
            "subset": "main"
        }
    """

    # Run just before CollectSubsets
    order = api.CollectorOrder + 0.1021
    label = "Collect Audio"
    hosts = ["nukestudio"]
    families = ["clip"]

    def process(self, instance):
        # Exclude non-tagged instances.
        tagged = False
        for tag in instance.data["tags"]:
            tag_data = dict(tag["metadata"])
            family = tag_data.get("tag.family", "")
            if family.lower() == "audio":
                subset = tag_data.get("tag.subset", "Main")
                tagged = True

        if not tagged:
            self.log.debug(
                "Skipping \"{}\" because its not tagged with "
                "\"audio\"".format(instance)
            )
            return

        # Collect data.
        data = {}
        for key, value in instance.data.iteritems():
            data[key] = value

        data["family"] = "audio"
        data["families"] = ["ftrack"]

        data["subset"] = "audio" + subset.title()

        data["source"] = data["sourcePath"]

        data["label"] = "{} - {} - ({})".format(
            data['asset'], data["subset"], os.path.splitext(data["sourcePath"])[
                1]
        )

        self.log.debug("Creating instance with data: {}".format(data))
        instance.context.create_instance(**data)
