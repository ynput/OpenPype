import sys
import json
import re
import os
import contextlib
from opentimelineio import opentime
import openpype

from ..otio import davinci_export as otio_export

from openpype.api import Logger

log = Logger().get_logger(__name__)

self = sys.modules[__name__]
self.project_manager = None
self.media_storage = None

# OpenPype sequencial rename variables
self.rename_index = 0
self.rename_add = 0

self.publish_clip_color = "Pink"
self.pype_marker_workflow = True

# OpenPype compound clip workflow variable
self.pype_tag_name = "VFX Notes"

# OpenPype marker workflow variables
self.pype_marker_name = "OpenPypeData"
self.pype_marker_duration = 1
self.pype_marker_color = "Mint"
self.temp_marker_frame = None

# OpenPype default timeline
self.pype_timeline_name = "OpenPypeTimeline"


@contextlib.contextmanager
def maintain_current_timeline(to_timeline: object,
                              from_timeline: object = None):
    """Maintain current timeline selection during context

    Attributes:
        from_timeline (resolve.Timeline)[optional]:
    Example:
        >>> print(from_timeline.GetName())
        timeline1
        >>> print(to_timeline.GetName())
        timeline2

        >>> with maintain_current_timeline(to_timeline):
        ...     print(get_current_timeline().GetName())
        timeline2

        >>> print(get_current_timeline().GetName())
        timeline1
    """
    project = get_current_project()
    working_timeline = from_timeline or project.GetCurrentTimeline()

    # swith to the input timeline
    project.SetCurrentTimeline(to_timeline)

    try:
        # do a work
        yield
    finally:
        # put the original working timeline to context
        project.SetCurrentTimeline(working_timeline)


def get_project_manager():
    # TODO: get_project_manager
    return


def get_media_storage():
    # TODO: get_media_storage
    return


def get_current_project():
    # TODO: get_current_project
    return


def get_current_timeline(new=False):
    # TODO: get_current_timeline
    return


def create_bin(name: str, root: object = None) -> object:
    # TODO: create_bin
    return
