import pyblish.api


class CollectFusionRenderMode(pyblish.api.InstancePlugin):
    """Collect current comp's render Mode

    Options:
        local
        farm

    Note that this value is set for each comp separately. When you save the
    comp this information will be stored in that file. If for some reason the
    available tool does not visualize which render mode is set for the
    current comp, please run the following line in the console (Py2)

    comp.GetData("pype.rendermode")

    This will return the name of the current render mode as seen above under
    Options.

    """

    order = pyblish.api.CollectorOrder + 0.4
    label = "Collect Render Mode"
    hosts = ["fusion"]
    families = ["render"]

    def process(self, instance):
        """Collect all image sequence tools"""
        options = ["local", "farm"]

        comp = instance.context.data.get("currentComp")
        if not comp:
            raise RuntimeError("No comp previously collected, unable to "
                               "retrieve Fusion version.")

        rendermode = comp.GetData("pype.rendermode") or "local"
        assert rendermode in options, "Must be supported render mode"

        self.log.info("Render mode: {0}".format(rendermode))

        # Append family
        family = "render.{0}".format(rendermode)
        instance.data["families"].append(family)
