"""Utility functions.

This module contains utility functions dedicated to frame range operations
"""
import clique

from openpype.lib import Logger

log = Logger.get_logger(__name__)


def get_frame_start_str(frame_start, frame_end):
    """Get frame start string.

    Args:
        frame_start (int): first frame
        frame_end (int): last frame

    Returns:
        str: frame start string
    """
    log.debug("frame_start, frame_end: {}, {}".format(frame_start, frame_end))
    last_frame_str = str(frame_end)
    max_padding_length = len(last_frame_str)
    formatting_str = "{{:0>{}}}".format(max_padding_length)

    log.debug("Formatting string: {}".format(formatting_str))
    # convert first frame to string with padding
    return formatting_str.format(frame_start)


def get_asset_frame_range(asset_name=None, asset_id=None, fields=None):
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
    from openpype.pipeline.context_tools import get_current_project_asset

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


def get_frame_range_from_list_of_files(collected_files):
    """Get frame range from sequence files.

    Args:
        collected_files (list[str]): list of files

    Returns:
        Any[tuple[int, int], tuple[None, None]]: frame range or None
            if not possible
    """

    collections, remainder = clique.assemble(collected_files)
    if not collections:
        # No sequences detected and we can't retrieve
        # frame range from single file
        return None, None

    collection = collections[0]
    repres_frames = list(collection.indexes)

    return repres_frames[0], repres_frames[-1]
