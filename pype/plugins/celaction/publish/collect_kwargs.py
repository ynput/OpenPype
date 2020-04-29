import pyblish.api
import pype.celaction


class CollectKwargs(pyblish.api.Collector):
    """ Collects all keyword arguments passed from the terminal """

    order = pyblish.api.Collector.order - 0.1

    def process(self, context):
        kwargs = pype.celaction.kwargs.copy()

        self.log.info("Converting nested lists to dict: %s" % kwargs)
        kwargs["data"] = dict(kwargs.get("data") or [])

        self.log.info("Storing kwargs: %s" % kwargs)
        context.set_data("kwargs", kwargs)
