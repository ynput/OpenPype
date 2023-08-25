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
    padding = len(str(frame_end))
    return str(frame_start).zfill(padding)


def get_asset_frame_range(project_name, asset_name, asset_doc=None):
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
    if not asset_doc:
        asset_doc = get_asset_by_name(
            project_name,
            asset_name,
            fields=[
                "data.frameStart",
                "data.frameEnd",
                "data.handleStart",
                "data.handleEnd"
            ]
        )
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

    assert len(collections) == 1, (
        "Multiple sequences detected in collected files"
    )

    collection = collections[0]
    repres_frames = list(collection.indexes)

    return repres_frames[0], repres_frames[-1]
