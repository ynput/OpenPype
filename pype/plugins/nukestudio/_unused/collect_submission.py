import pyblish.api


class CollectSubmission(pyblish.api.ContextPlugin):
    """Collect submisson children."""

    order = pyblish.api.CollectorOrder - 0.1

    def process(self, context):
        import hiero

        if hasattr(hiero, "submission"):
            context.data["submission"] = hiero.submission
            self.log.debug("__ submission: {}".format(context.data["submission"]))
