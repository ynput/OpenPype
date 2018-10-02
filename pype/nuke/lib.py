import sys

from avalon.vendor.Qt import QtGui
import avalon.nuke

import nuke

self = sys.modules[__name__]
self._project = None


def update_frame_range(start, end, root=None):
    """Set Nuke script start and end frame range

    Args:
        start (float, int): start frame
        end (float, int): end frame
        root (object, Optional): root object from nuke's script

    Returns:
        None

    """

    knobs = {
        "first_frame": start,
        "last_frame": end
    }

    with avalon.nuke.viewer_update_and_undo_stop():
        for key, value in knobs.items():
            if root:
                root[key].setValue(value)
            else:
                nuke.root()[key].setValue(value)


def get_additional_data(container):
    """Get Nuke's related data for the container

    Args:
        container(dict): the container found by the ls() function

    Returns:
        dict
    """

    node = container["_tool"]
    tile_color = node['tile_color'].value()
    if tile_color is None:
        return {}

    hex = '%08x' % tile_color
    rgba = [
        float(int(hex[0:2], 16)) / 255.0,
        float(int(hex[2:4], 16)) / 255.0,
        float(int(hex[4:6], 16)) / 255.0
    ]

    return {"color": QtGui.QColor().fromRgbF(rgba[0], rgba[1], rgba[2])}
