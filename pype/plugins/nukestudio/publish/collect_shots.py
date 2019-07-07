from pyblish import api


class CollectShots(api.ContextPlugin):
    """Collect Shot from Clip."""

    # Run just before CollectClipSubsets
    order = api.CollectorOrder + 0.1025
    label = "Collect Shots"
    hosts = ["nukestudio"]
    families = ["clip"]

    def process(self, context):
        for instance in context[:]:
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
                continue

            # Collect data.
            data = {}
            for key, value in instance.data.iteritems():
                data[key] = value

            data["family"] = "shot"
            data["families"] = []
            data["frameStart"] = instance.data.get("frameStart", 1)

            data["label"] += " - tasks: {} - assetbuilds: {}".format(
                data["tasks"], [x["name"] for x in data.get("assetbuilds", [])]
            )

            # Get handles.
            data["handleStart"] = instance.data["handleStart"]
            data["handleStart"] += data["handles"]
            data["handleEnd"] = instance.data["handleEnd"] + data["handles"]

            # Frame-ranges with handles.
            data["sourceInH"] = data["sourceIn"] - data["handleStart"]
            data["sourceOutH"] = data["sourceOut"] + data["handleEnd"]

            # Get timeline frames.
            data["timelineIn"] = int(data["item"].timelineIn())
            data["timelineOut"] = int(data["item"].timelineOut())

            # Frame-ranges with handles.
            data["timelineInHandles"] = data["timelineIn"]
            data["timelineInHandles"] -= data["handleStart"]
            data["timelineOutHandles"] = data["timelineOut"]
            data["timelineOutHandles"] += data["handleEnd"]

            # Creating comp frame range.
            data["endFrame"] = (
                data["frameStart"] + (data["sourceOut"] - data["sourceIn"])
            )

            # Get fps.
            sequence = instance.context.data["activeSequence"]
            data["fps"] = sequence.framerate()

            # Create instance.
            self.log.debug("Creating instance with: {}".format(data))
            instance.context.create_instance(**data)
