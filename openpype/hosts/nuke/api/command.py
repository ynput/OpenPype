import logging
import contextlib
import nuke
from bson.objectid import ObjectId

from openpype.pipeline import legacy_io

log = logging.getLogger(__name__)


def reset_frame_range():
    """ Set frame range to current asset
        Also it will set a Viewer range with
        displayed handles
    """

    fps = float(legacy_io.Session.get("AVALON_FPS", 25))

    nuke.root()["fps"].setValue(fps)
    name = legacy_io.Session["AVALON_ASSET"]
    asset = legacy_io.find_one({"name": name, "type": "asset"})
    asset_data = asset["data"]

    handles = get_handles(asset)

    frame_start = int(asset_data.get(
        "frameStart",
        asset_data.get("edit_in")))

    frame_end = int(asset_data.get(
        "frameEnd",
        asset_data.get("edit_out")))

    if not all([frame_start, frame_end]):
        missing = ", ".join(["frame_start", "frame_end"])
        msg = "'{}' are not set for asset '{}'!".format(missing, name)
        log.warning(msg)
        nuke.message(msg)
        return

    frame_start -= handles
    frame_end += handles

    nuke.root()["first_frame"].setValue(frame_start)
    nuke.root()["last_frame"].setValue(frame_end)

    # setting active viewers
    vv = nuke.activeViewer().node()
    vv["frame_range_lock"].setValue(True)
    vv["frame_range"].setValue("{0}-{1}".format(
        int(asset_data["frameStart"]),
        int(asset_data["frameEnd"]))
    )


def get_handles(asset):
    """ Gets handles data

    Arguments:
        asset (dict): avalon asset entity

    Returns:
        handles (int)
    """
    data = asset["data"]
    if "handles" in data and data["handles"] is not None:
        return int(data["handles"])

    parent_asset = None
    if "visualParent" in data:
        vp = data["visualParent"]
        if vp is not None:
            parent_asset = legacy_io.find_one({"_id": ObjectId(vp)})

    if parent_asset is None:
        parent_asset = legacy_io.find_one({"_id": ObjectId(asset["parent"])})

    if parent_asset is not None:
        return get_handles(parent_asset)
    else:
        return 0


def reset_resolution():
    """Set resolution to project resolution."""
    project = legacy_io.find_one({"type": "project"})
    p_data = project["data"]

    width = p_data.get("resolution_width",
                       p_data.get("resolutionWidth"))
    height = p_data.get("resolution_height",
                        p_data.get("resolutionHeight"))

    if not all([width, height]):
        missing = ", ".join(["width", "height"])
        msg = "No resolution information `{0}` found for '{1}'.".format(
            missing,
            project["name"])
        log.warning(msg)
        nuke.message(msg)
        return

    current_width = nuke.root()["format"].value().width()
    current_height = nuke.root()["format"].value().height()

    if width != current_width or height != current_height:

        fmt = None
        for f in nuke.formats():
            if f.width() == width and f.height() == height:
                fmt = f.name()

        if not fmt:
            nuke.addFormat(
                "{0} {1} {2}".format(int(width), int(height), project["name"])
            )
            fmt = project["name"]

        nuke.root()["format"].setValue(fmt)


@contextlib.contextmanager
def viewer_update_and_undo_stop():
    """Lock viewer from updating and stop recording undo steps"""
    try:
        # stop active viewer to update any change
        viewer = nuke.activeViewer()
        if viewer:
            viewer.stop()
        else:
            log.warning("No available active Viewer")
        nuke.Undo.disable()
        yield
    finally:
        nuke.Undo.enable()
