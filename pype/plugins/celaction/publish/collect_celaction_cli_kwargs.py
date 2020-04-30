import pyblish.api
import pype.celaction


class CollectCelactionCliKwargs(pyblish.api.Collector):
    """ Collects all keyword arguments passed from the terminal """
    
    label = "Collect Celaction Cli Kwargs"
    order = pyblish.api.Collector.order - 0.1

    def process(self, context):
        kwargs = pype.celaction.kwargs.copy()

        self.log.info("Storing kwargs: %s" % kwargs)
        context.set_data("kwargs", kwargs)

        # get kwargs onto context data as keys with values
        for k, v in kwargs.items():
            self.log.info(f"Setting `{k}` to instance.data with value: `{v}`")
            context.data[k] = v
