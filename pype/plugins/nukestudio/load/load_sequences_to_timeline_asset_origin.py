from avalon import api
import hiero
from pype.hosts.nukestudio import lib
reload(lib)


class LoadSequencesToTimelineAssetOrigin(api.Loader):
    """Load image sequence into Hiero timeline

    Place clip to timeline on its asset origin timings collected
    during conforming to project
    """

    families = ["render2d", "source", "plate", "render"]
    representations = ["exr", "dpx", "jpg", "jpeg", "png"]

    label = "Load to timeline with shot origin timing"
    order = -10
    icon = "code-fork"
    color = "orange"

    def load(self, context, name, namespace, data):

        data.update({
            # "projectBinPath": "Loaded",
            "hieroWorkfileName": hiero.ui.activeProject().name()
            })

        self.log.debug("_ context: `{}`".format(context))
        self.log.debug("_ representation._id: `{}`".format(
            context["representation"]["_id"]))

        clip_loader = lib.ClipLoader(self, context, **data)
        clip_loader.load()

        self.log.info("Loader done: `{}`".format(name))

    def switch(self, container, representation):
        self.update(container, representation)

    def update(self, container, representation):
        """ Updating previously loaded clips
        """
        pass

    def remove(self, container):
        """ Removing previously loaded clips
        """
        pass
