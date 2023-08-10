"""Utility functions.

This module contains utility functions dedicated to operations


"""
from openpype.pipeline.context_tools import get_current_project_asset


def get_frame_start_str(first_frame, last_frame):
    """Get frame start string.

    Args:
        first_frame (int): first frame
        last_frame (int): last frame

    Returns:
        str: frame start string
    """
    # convert first frame to string with padding
    return (
        "{{:0{}d}}".format(len(str(last_frame)))
    ).format(first_frame)


def get_frame_range(asset_name=None, asset_id=None, fields=None):
    """Get the current assets frame range and handles.

    Args:
        asset_name Optional[str]: Name of asset used for filter.
        asset_id Optional[Union[str, ObjectId]]: Asset document id.
            If entered then is used as only filter.
        fields Optional[Union[List[str], None]]: Limit returned data
            of asset documents to specific keys.
    Returns:
        dict: with frame start, frame end, handle start, handle end.
    """
    # Set frame start/end
    asset = get_current_project_asset()
    frame_start = asset["data"].get("frameStart")
    frame_end = asset["data"].get("frameEnd")

    if frame_start is None or frame_end is None:
        return

    handle_start = asset["data"].get("handleStart", 0)
    handle_end = asset["data"].get("handleEnd", 0)

    return {
        "frameStart": frame_start,
        "frameEnd": frame_end,
        "handleStart": handle_start,
        "handleEnd": handle_end
    }
