import pyblish.api

import hiero


class CollectSelection(pyblish.api.ContextPlugin):
    """Inject the selection in the context."""

    order = pyblish.api.CollectorOrder - 0.1
    label = "Selection"

    def process(self, context):
        selection = list(hiero.selection)

        self.log.debug("selection: {}".format(selection))

        if not selection:
            self.log.debug(
                "Nothing is selected. Collecting all items from sequence "
                "\"{}\"".format(hiero.ui.activeSequence())
            )
            for track in hiero.ui.activeSequence().items():
                selection.extend(track.items())

        context.data["selection"] = selection
