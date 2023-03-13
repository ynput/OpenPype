import pyblish.api
from pprint import pformat


class CollectFusionRenders(pyblish.api.InstancePlugin):
    """Collect current comp's render Mode

    Options:
        local
        farm

    Note that this value is set for each comp separately. When you save the
    comp this information will be stored in that file. If for some reason the
    available tool does not visualize which render mode is set for the
    current comp, please run the following line in the console (Py2)

    comp.GetData("openpype.rendermode")

    This will return the name of the current render mode as seen above under
    Options.

    """

    order = pyblish.api.CollectorOrder + 0.4
    label = "Collect Renders"
    hosts = ["fusion"]
    families = ["render"]

    def process(self, instance):
        self.log.debug(pformat(instance.data))

        saver_node = instance.data["transientData"]["tool"]
        render_target = instance.data["render_target"]
        family = instance.data["family"]
        families = instance.data["families"]

        # add targeted family to families
        instance.data["families"].append(
            "{}.{}".format(family, render_target)
        )

        self.log.debug(pformat(instance.data))
