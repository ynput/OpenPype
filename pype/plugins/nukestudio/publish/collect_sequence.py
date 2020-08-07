from pyblish import api
import hiero


class CollectSequence(api.ContextPlugin):
    """Collect all Track items selection."""

    order = api.CollectorOrder - 0.01
    label = "Collect Sequence"
    hosts = ["nukestudio"]

    def process(self, context):
        context.data['activeSequence'] = hiero.ui.activeSequence()
