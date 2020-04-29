import os
import pyblish.api
import pype.celaction


class CollectData(pyblish.api.Collector):
    """Collects data passed from via CLI"""

    order = pyblish.api.Collector.order - 0.1

    def process(self, context):
        self.log.info("Adding data from command-line into Context..")

        kwargs = pype.celaction.kwargs.copy()

        for key, value in kwargs.items():
            self.log.info("%s = %s" % (key, value))
            context.set_data(key, value)
