import os
import sys
import re
import contextlib

from bson.objectid import ObjectId
from Qt import QtGui

from avalon import io
from openpype.pipeline import switch_container
from .pipeline import get_current_comp, comp_lock_and_undo_chunk
from openpype.api import (
    get_asset
)
self = sys.modules[__name__]
self._project = None


def update_frame_range(start, end, comp=None, set_render_range=True, **kwargs):
    """Set Fusion comp's start and end frame range

    Args:
        start (float, int): start frame
        end (float, int): end frame
        comp (object, Optional): comp object from fusion
        set_render_range (bool, Optional): When True this will also set the
            composition's render start and end frame.
        kwargs (dict): additional kwargs

    Returns:
        None

    """

    if not comp:
        comp = get_current_comp()

    attrs = {
        "COMPN_GlobalStart": start,
        "COMPN_GlobalEnd": end
    }

    # exclude handles if any found in kwargs
    if kwargs.get("handle_start"):
        handle_start = kwargs.get("handle_start")
        attrs["COMPN_GlobalStart"] = int(start - handle_start)

    if kwargs.get("handle_end"):
        handle_end = kwargs.get("handle_end")
        attrs["COMPN_GlobalEnd"] = int(end + handle_end)

    # set frame range
    if set_render_range:
        attrs.update({
            "COMPN_RenderStart": start,
            "COMPN_RenderEnd": end
        })

    with comp_lock_and_undo_chunk(comp):
        comp.SetAttrs(attrs)


def set_framerange():
    asset_doc = get_asset()
    start = asset_doc["data"]["frameStart"]
    end = asset_doc["data"]["frameEnd"]

    data = {
        "handle_start": asset_doc["data"]["handleStart"],
        "handle_end": asset_doc["data"]["handleEnd"]
    }
    update_frame_range(start, end, set_render_range=True, **data)


def get_additional_data(container):
    """Get Fusion related data for the container

    Args:
        container(dict): the container found by the ls() function

    Returns:
        dict
    """

    tool = container["_tool"]
    tile_color = tool.TileColor
    if tile_color is None:
        return {}

    return {"color": QtGui.QColor.fromRgbF(tile_color["R"],
                                           tile_color["G"],
                                           tile_color["B"])}


def switch_item(container,
                asset_name=None,
                subset_name=None,
                representation_name=None):
    """Switch container asset, subset or representation of a container by name.

    It'll always switch to the latest version - of course a different
    approach could be implemented.

    Args:
        container (dict): data of the item to switch with
        asset_name (str): name of the asset
        subset_name (str): name of the subset
        representation_name (str): name of the representation

    Returns:
        dict

    """

    if all(not x for x in [asset_name, subset_name, representation_name]):
        raise ValueError("Must have at least one change provided to switch.")

    # Collect any of current asset, subset and representation if not provided
    # so we can use the original name from those.
    if any(not x for x in [asset_name, subset_name, representation_name]):
        _id = ObjectId(container["representation"])
        representation = io.find_one({"type": "representation", "_id": _id})
        version, subset, asset, project = io.parenthood(representation)

        if asset_name is None:
            asset_name = asset["name"]

        if subset_name is None:
            subset_name = subset["name"]

        if representation_name is None:
            representation_name = representation["name"]

    # Find the new one
    asset = io.find_one({
        "name": asset_name,
        "type": "asset"
    })
    assert asset, ("Could not find asset in the database with the name "
                   "'%s'" % asset_name)

    subset = io.find_one({
        "name": subset_name,
        "type": "subset",
        "parent": asset["_id"]
    })
    assert subset, ("Could not find subset in the database with the name "
                    "'%s'" % subset_name)

    version = io.find_one(
        {
            "type": "version",
            "parent": subset["_id"]
        },
        sort=[('name', -1)]
    )

    assert version, "Could not find a version for {}.{}".format(
        asset_name, subset_name
    )

    representation = io.find_one({
        "name": representation_name,
        "type": "representation",
        "parent": version["_id"]}
    )

    assert representation, ("Could not find representation in the database "
                            "with the name '%s'" % representation_name)

    switch_container(container, representation)

    return representation


@contextlib.contextmanager
def maintained_selection():
    comp = get_current_comp()
    previous_selection = comp.GetToolList(True).values()
    try:
        yield
    finally:
        flow = comp.CurrentFrame.FlowView
        flow.Select()  # No args equals clearing selection
        if previous_selection:
            for tool in previous_selection:
                flow.Select(tool, True)


def get_frame_path(path):
    """Get filename for the Fusion Saver with padded number as '#'

    >>> get_frame_path("C:/test.exr")
    ('C:/test', 4, '.exr')

    >>> get_frame_path("filename.00.tif")
    ('filename.', 2, '.tif')

    >>> get_frame_path("foobar35.tif")
    ('foobar', 2, '.tif')

    Args:
        path (str): The path to render to.

    Returns:
        tuple: head, padding, tail (extension)

    """
    filename, ext = os.path.splitext(path)

    # Find a final number group
    match = re.match('.*?([0-9]+)$', filename)
    if match:
        padding = len(match.group(1))
        # remove number from end since fusion
        # will swap it with the frame number
        filename = filename[:-padding]
    else:
        padding = 4  # default Fusion padding

    return filename, padding, ext
