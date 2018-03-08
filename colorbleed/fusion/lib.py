import sys

import avalon.fusion


self = sys.modules[__name__]
self._project = None


def update_frame_range(start, end, comp=None, set_render_range=True):
    """Set Fusion comp's start and end frame range

    Args:
        start (float, int): start frame
        end (float, int): end frame
        comp (object, Optional): comp object from fusion
        set_render_range (bool, Optional): When True this will also set the
            composition's render start and end frame.

    Returns:
        None

    """

    if not comp:
        comp = avalon.fusion.get_current_comp()

    attrs = {
        "COMPN_GlobalStart": start,
        "COMPN_GlobalEnd": end
    }

    if set_render_range:
        attrs.update({
            "COMPN_RenderStart": start,
            "COMPN_RenderEnd": end
        })

    with avalon.fusion.comp_lock_and_undo_chunk(comp):
        comp.SetAttrs(attrs)
