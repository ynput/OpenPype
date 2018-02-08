from avalon import api


class FusionLoadAlembicCamera(api.Loader):
    """Load image sequence into Fusion"""

    families = ["colorbleed.camera"]
    representations = ["ma"]

    label = "Load sequence"
    order = -10
    icon = "play-circle"
    color = "orange"

    def load(self, context, name, namespace, data):
        """"""

        from avalon.fusion import (imprint_container,
                                   get_current_comp,
                                   comp_lock_and_undo_chunk)

        current_comp = get_current_comp()
        with comp_lock_and_undo_chunk(current_comp):
            tool = current_comp.SurfaceAlembicMesh()
            tool.SetData("TOOLS_NameSet", )

        pass
