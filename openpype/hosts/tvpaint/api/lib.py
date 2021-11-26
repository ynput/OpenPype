from PIL import Image

import avalon.io
from avalon.tvpaint.lib import execute_george


def set_context_settings(asset_doc=None):
    """Set workfile settings by asset document data.

    Change fps, resolution and frame start/end.
    """
    if asset_doc is None:
        # Use current session asset if not passed
        asset_doc = avalon.io.find_one({
            "type": "asset",
            "name": avalon.io.Session["AVALON_ASSET"]
        })

    project_doc = avalon.io.find_one({"type": "project"})

    framerate = asset_doc["data"].get("fps")
    if framerate is None:
        framerate = project_doc["data"].get("fps")

    if framerate is not None:
        execute_george(
            "tv_framerate {} \"timestretch\"".format(framerate)
        )
    else:
        print("Framerate was not found!")

    width_key = "resolutionWidth"
    height_key = "resolutionHeight"

    width = asset_doc["data"].get(width_key)
    height = asset_doc["data"].get(height_key)
    if width is None or height is None:
        width = project_doc["data"].get(width_key)
        height = project_doc["data"].get(height_key)

    if width is None or height is None:
        print("Resolution was not found!")
    else:
        execute_george("tv_resizepage {} {} 0".format(width, height))

    frame_start = asset_doc["data"].get("frameStart")
    frame_end = asset_doc["data"].get("frameEnd")

    if frame_start is None or frame_end is None:
        print("Frame range was not found!")
        return

    handles = asset_doc["data"].get("handles") or 0
    handle_start = asset_doc["data"].get("handleStart")
    handle_end = asset_doc["data"].get("handleEnd")

    if handle_start is None or handle_end is None:
        handle_start = handles
        handle_end = handles

    # Always start from 0 Mark In and set only Mark Out
    mark_in = 0
    mark_out = mark_in + (frame_end - frame_start) + handle_start + handle_end

    execute_george("tv_markin {} set".format(mark_in))
    execute_george("tv_markout {} set".format(mark_out))
