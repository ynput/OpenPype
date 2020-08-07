from pyblish import api


class CollectClipTagTasks(api.InstancePlugin):
    """Collect Tags from selected track items."""

    order = api.CollectorOrder + 0.012
    label = "Collect Tag Tasks"
    hosts = ["nukestudio"]
    families = ['clip']

    def process(self, instance):
        # gets tags
        tags = instance.data["tags"]

        tasks = list()
        for t in tags:
            t_metadata = dict(t["metadata"])
            t_family = t_metadata.get("tag.family", "")

            # gets only task family tags and collect labels
            if "task" in t_family:
                t_task = t_metadata.get("tag.label", "")
                tasks.append(t_task)

        instance.data["tasks"] = tasks

        self.log.info("Collected Tasks from Tags: `{}`".format(
            instance.data["tasks"]))
        return
