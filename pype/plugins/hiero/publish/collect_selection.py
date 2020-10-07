import pyblish.api

import hiero


class CollectSelection(pyblish.api.ContextPlugin):
    """Inject the selection in the context."""

    order = pyblish.api.CollectorOrder - 0.1
    label = "Selection"

    def process(self, context):
        selection = list(hiero.selection)

        self.log.debug("selection: {}".format(selection))

        context.data["selection"] = selection
