import pyblish.api


class CollectSource(pyblish.api.ContextPlugin):
    """Collecting instances from traypublisher host."""

    label = "Collect source"
    order = pyblish.api.CollectorOrder - 0.49
    hosts = ["traypublisher"]

    def process(self, context):
        # get json paths from os and load them
        source_name = "traypublisher"
        for instance in context:
            source = instance.data.get("source")
            if not source:
                instance.data["source"] = source_name
                self.log.info((
                    "Source of instance \"{}\" is changed to \"{}\""
                ).format(instance.data["name"], source_name))
            else:
                self.log.info((
                    "Source of instance \"{}\" was already set to \"{}\""
                ).format(instance.data["name"], source))
