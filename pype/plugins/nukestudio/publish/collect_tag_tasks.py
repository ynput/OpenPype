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

        # gets presets for nukestudio
        presets = instance.context.data['presets'][
            instance.context.data['host']]

        # find preset for default task
        default_tasks = presets['rules_tasks']['defaultTasks']

        tasks = list()
        for t in tags:
            t_metadata = dict(t["metadata"])
            t_family = t_metadata.get("tag.family", "")

            # gets only task family tags and collect labels
            if "task" in t_family:
                t_task = t_metadata.get("tag.label", "")
                tasks.append(t_task)

        if tasks:
            instance.data["tasks"] = tasks
        else:
            # add tasks from presets if no task tag
            instance.data["tasks"] = default_tasks

        self.log.info("Collected Tasks from Tags: `{}`".format(
            instance.data["tasks"]))
        return
