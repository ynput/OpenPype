"""A module containing generic loader actions that will display in the Loader.

"""

from avalon import api


def _set_frame_range(start, end, set_render_range=True):
    """Set Fusion comp's start and end frame range

    Attrs:
        set_render_range (bool, Optional): When True this will also set the
            composition's render start and end frame.

    Returns:
        None

    """

    from avalon.fusion import get_current_comp, comp_lock_and_undo_chunk

    comp = get_current_comp()

    attrs = {
        "COMPN_GlobalStart": start,
        "COMPN_GlobalEnd": end
    }

    if set_render_range:
        attrs.update({
            "COMPN_RenderStart": start,
            "COMPN_RenderEnd": end
        })

    with comp_lock_and_undo_chunk(comp):
        comp.SetAttrs(attrs)


class FusionSetFrameRangeLoader(api.Loader):
    """Specific loader of Alembic for the avalon.animation family"""

    families = ["colorbleed.animation",
                "colorbleed.camera",
                "colorbleed.imagesequence",
                "colorbleed.yeticache",
                "colorbleed.pointcache"]
    representations = ["*"]

    label = "Set frame range"
    order = 11
    icon = "clock-o"
    color = "white"

    def load(self, context, name, namespace, data):

        version = context['version']
        version_data = version.get("data", {})

        start = version_data.get("startFrame", None)
        end = version_data.get("endFrame", None)

        if start is None or end is None:
            print("Skipping setting frame range because start or "
                  "end frame data is missing..")
            return

        _set_frame_range(start, end)


class FusionSetFrameRangeWithHandlesLoader(api.Loader):
    """Specific loader of Alembic for the avalon.animation family"""

    families = ["colorbleed.animation",
                "colorbleed.camera",
                "colorbleed.imagesequence",
                "colorbleed.yeticache",
                "colorbleed.pointcache"]
    representations = ["*"]

    label = "Set frame range (with handles)"
    order = 12
    icon = "clock-o"
    color = "white"

    def load(self, context, name, namespace, data):

        version = context['version']
        version_data = version.get("data", {})

        start = version_data.get("startFrame", None)
        end = version_data.get("endFrame", None)

        if start is None or end is None:
            print("Skipping setting frame range because start or "
                  "end frame data is missing..")
            return

        # Include handles
        handles = version_data.get("handles", 0)
        start -= handles
        end += handles

        _set_frame_range(start, end)
