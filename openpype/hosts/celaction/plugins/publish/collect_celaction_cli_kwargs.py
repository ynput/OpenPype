import pyblish.api
import sys
from pprint import pformat


class CollectCelactionCliKwargs(pyblish.api.Collector):
    """ Collects all keyword arguments passed from the terminal """

    label = "Collect Celaction Cli Kwargs"
    order = pyblish.api.Collector.order - 0.1

    def process(self, context):
        args = list(sys.argv[1:])
        self.log.info(str(args))
        missing_kwargs = []
        passing_kwargs = {}
        for key in (
            "chunk",
            "frameStart",
            "frameEnd",
            "resolutionWidth",
            "resolutionHeight",
            "currentFile",
        ):
            arg_key = f"--{key}"
            if arg_key not in args:
                missing_kwargs.append(key)
                continue
            arg_idx = args.index(arg_key)
            args.pop(arg_idx)
            if key != "currentFile":
                value = args.pop(arg_idx)
            else:
                path_parts = []
                while arg_idx < len(args):
                    path_parts.append(args.pop(arg_idx))
                value = " ".join(path_parts).strip('"')

            passing_kwargs[key] = value

        if missing_kwargs:
            self.log.debug("Missing arguments {}".format(
                ", ".join(
                    [f'"{key}"' for key in missing_kwargs]
                )
            ))

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
