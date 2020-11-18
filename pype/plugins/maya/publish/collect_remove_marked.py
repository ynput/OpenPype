import pyblish.api


class CollectRemoveMarked(pyblish.api.ContextPlugin):
    """Collect model data

    Ensures always only a single frame is extracted (current frame).

    Note:
        This is a workaround so that the `pype.model` family can use the
        same pointcache extractor implementation as animation and pointcaches.
        This always enforces the "current" frame to be published.

    """

    order = pyblish.api.CollectorOrder + 0.499
    label = 'Remove Marked Instances'

    def process(self, context):

        self.log.debug(context)
        # make ftrack publishable
        instances_to_remove = []
        for instance in context:
            if instance.data.get('remove'):
                instances_to_remove.append(instance)

        for instance in instances_to_remove:
            context.remove(instance)
