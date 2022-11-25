import pyblish.api
from openpype.hosts.celaction import scripts


class CollectCelactionCliKwargs(pyblish.api.Collector):
    """ Collects all keyword arguments passed from the terminal """

    label = "Collect Celaction Cli Kwargs"
    order = pyblish.api.Collector.order - 0.1

    def process(self, context):
        passing_kwargs = scripts.PASSING_KWARGS.copy()

        self.log.info("Storing kwargs: %s" % kwargs)
        context.set_data("passingKwargs", passing_kwargs)

        # get kwargs onto context data as keys with values
        for k, v in passing_kwargs.items():
            self.log.info(f"Setting `{k}` to instance.data with value: `{v}`")
            if k in ["frameStart", "frameEnd"]:
                context.data[k] = passing_kwargs[k] = int(v)
            else:
                context.data[k] = v
