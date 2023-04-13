import logging

import rv
from openpype.pipeline.context_tools import get_current_project_asset

log = logging.getLogger(__name__)


def reset_frame_range():
    """ Set timeline frame range.
    """
    asset_doc = get_current_project_asset()
    asset_data = asset_doc["data"]

    frame_start = int(asset_data.get(
        "frameStart",
        asset_data.get("edit_in")))

    frame_end = int(asset_data.get(
        "frameEnd",
        asset_data.get("edit_out")))

    rv.commands.setFrameStart(frame_start)
    rv.commands.setFrameEnd(frame_end)
    rv.commands.setFrame(frame_start)

    log.info("Project frame range set")


def set_session_fps():
    """ Set session fps.
    """
    asset_doc = get_current_project_asset()
    asset_data = asset_doc["data"]
    fps = float(asset_data.get("fps", 25))
    rv.commands.setFPS(fps)


def create_support_ticket():
    import webbrowser
    webbrowser.open("http://localhost:5400/tickets/create_tickets")
