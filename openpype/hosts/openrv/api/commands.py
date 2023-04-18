import logging

import rv
from openpype.pipeline.context_tools import get_current_project_asset

log = logging.getLogger(__name__)


def reset_frame_range():
    """ Set timeline frame range.
    """
    asset_doc = get_current_project_asset()
    asset_name = asset_doc["name"]
    asset_data = asset_doc["data"]

    frame_start = asset_data.get("frameStart")
    frame_end = asset_data.get("frameEnd")

    if frame_start is None or frame_end is None:
        log.warning("No edit information found for {}".format(asset_name))
        return

    rv.commands.setFrameStart(frame_start)
    rv.commands.setFrameEnd(frame_end)
    rv.commands.setFrame(frame_start)


def set_session_fps():
    """ Set session fps.
    """
    asset_doc = get_current_project_asset()
    asset_data = asset_doc["data"]
    fps = float(asset_data.get("fps", 25))
    rv.commands.setFPS(fps)
