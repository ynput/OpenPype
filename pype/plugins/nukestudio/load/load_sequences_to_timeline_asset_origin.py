from avalon import api


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
        pass

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
