from pyblish import api


class CollectShot(api.InstancePlugin):
    """Collect Shot from Clip."""

    # Run just before CollectSubsets
    order = api.CollectorOrder + 0.1025
    label = "Collect Shot"
    hosts = ["nukestudio"]
    families = ["clip"]

    def process(self, instance):
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

        context = instance.context

        # Collect data.
        data = {}
        for key, value in instance.data.iteritems():
            data[key] = value

        data["family"] = "shot"
        data["families"] = []
        data["frameStart"] = 1

        data["label"] += " - tasks: {} - assetbuilds: {}".format(
            data["tasks"], [x["name"] for x in data["assetBuilds"]]
        )

        # Get handles.
        data["handleStart"] = instance.data["handleStart"] + data["handles"]
        data["handleEnd"] = instance.data["handleEnd"] + data["handles"]

        # Frame-ranges with handles.
        data["sourceInH"] = data["sourceIn"] - data["handleStart"]
        data["sourceOutH"] = data["sourceOut"] + data["handleEnd"]

        # Get timeline frames.
        data["timelineIn"] = int(data["item"].timelineIn())
        data["timelineOut"] = int(data["item"].timelineOut())

        # Frame-ranges with handles.
        data["timelineInHandles"] = data["timelineIn"] - data["handleStart"]
        data["timelineOutHandles"] = data["timelineOut"] + data["handleEnd"]

        # Creating comp frame range.
        data["endFrame"] = (
            data["frameStart"] + (data["sourceOut"] - data["sourceIn"])
        )

        # Get fps.
        sequence = context.data["activeSequence"]
        data["fps"] = sequence.framerate()

        # Create instance.
        self.log.debug("Creating instance with: {}".format(data))
        context.create_instance(**data)
