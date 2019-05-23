from pyblish import api
import hiero


class CollectSequence(api.ContextPlugin):
    """Collect all Track items selection."""

    order = api.CollectorOrder
    label = "Collect Sequence"
    hosts = ["nukestudio"]

    def process(self, context):
        context.data['activeSequence'] = hiero.ui.activeSequence()
