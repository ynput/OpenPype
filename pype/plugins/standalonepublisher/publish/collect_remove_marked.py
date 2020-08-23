import pyblish.api


class CollectRemoveMarked(pyblish.api.ContextPlugin):
    """Clean up instances marked for removal

    Note:
        This is a workaround for race conditions and removing of instances
        used to generate other instances.

    """

    order = pyblish.api.CollectorOrder + 0.499
    label = 'Remove Marked Instances'

    def process(self, context):
        remove = []
        for instance in context:
            self.log.info("Checkng for removal...")
            self.log.info(instance)
            self.log.info(instance.data)
            if instance.data.get('remove'):
                remove.append(instance)

        self.log.debug(remove)

