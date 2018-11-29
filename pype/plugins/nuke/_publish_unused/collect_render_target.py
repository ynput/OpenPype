import pyblish.api


class CollectNukeRenderMode(pyblish.api.InstancePlugin):
    # TODO: rewrite docstring to nuke
    """Collect current comp's render Mode

    Options:
        local
        deadline

    Note that this value is set for each comp separately. When you save the
    comp this information will be stored in that file. If for some reason the
    available tool does not visualize which render mode is set for the
    current comp, please run the following line in the console (Py2)

    comp.GetData("rendermode")

    This will return the name of the current render mode as seen above under
    Options.

    """

    order = pyblish.api.CollectorOrder + 0.4
    label = "Collect Render Mode"
    hosts = ["nuke"]
    families = ["write", "render.local"]

    def process(self, instance):
        """Collect all image sequence tools"""
        options = ["local", "deadline"]

        node = instance[0]

        if bool(node["render_local"].getValue()):
            rendermode = "local"
        else:
            rendermode = "deadline"

        assert rendermode in options, "Must be supported render mode"

        # Append family
        instance.data["families"].remove("render")
        family = "render.{0}".format(rendermode)
        instance.data["families"].append(family)

        self.log.info("Render mode: {0}".format(rendermode))
