import pyblish.api
import argparse
import sys
from pprint import pformat


class CollectCelactionCliKwargs(pyblish.api.Collector):
    """ Collects all keyword arguments passed from the terminal """

    label = "Collect Celaction Cli Kwargs"
    order = pyblish.api.Collector.order - 0.1

    def process(self, context):
        parser = argparse.ArgumentParser(prog="celaction")
        parser.add_argument("--currentFile",
                            help="Pass file to Context as `currentFile`")
        parser.add_argument("--chunk",
                            help=("Render chanks on farm"))
        parser.add_argument("--frameStart",
                            help=("Start of frame range"))
        parser.add_argument("--frameEnd",
                            help=("End of frame range"))
        parser.add_argument("--resolutionWidth",
                            help=("Width of resolution"))
        parser.add_argument("--resolutionHeight",
                            help=("Height of resolution"))
        passing_kwargs = parser.parse_args(sys.argv[1:]).__dict__

        self.log.info("Storing kwargs ...")
        self.log.debug("_ passing_kwargs: {}".format(pformat(passing_kwargs)))

        # set kwargs to context data
        context.set_data("passingKwargs", passing_kwargs)

        # get kwargs onto context data as keys with values
        for k, v in passing_kwargs.items():
            self.log.info(f"Setting `{k}` to instance.data with value: `{v}`")
            if k in ["frameStart", "frameEnd"]:
                context.data[k] = passing_kwargs[k] = int(v)
            else:
                context.data[k] = v
