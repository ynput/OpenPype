from pyblish import api


class CollectClipTagTasks(api.InstancePlugin):
    """Collect Tags from selected track items."""

    order = api.CollectorOrder - 0.077
    label = "Collect Tag Tasks"
    hosts = ["hiero"]
    families = ["shot"]

    def process(self, instance):
        # gets tags
        tags = instance.data["tags"]

        tasks = {}
        for tag in tags:
            t_metadata = dict(tag.metadata())
            t_family = t_metadata.get("tag.family", "")

            # gets only task family tags and collect labels
            if "task" in t_family:
                t_task_name = t_metadata.get("tag.label", "")
                t_task_type = t_metadata.get("tag.type", "")
                tasks[t_task_name] = {"type": t_task_type}

        instance.data["tasks"] = tasks

        self.log.info("Collected Tasks from Tags: `{}`".format(
            instance.data["tasks"]))
        return
