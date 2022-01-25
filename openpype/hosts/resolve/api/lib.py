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

# OpenPype sequential rename variables
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

    # switch to the input timeline
    project.SetCurrentTimeline(to_timeline)

    try:
        # do a work
        yield
    finally:
        # put the original working timeline to context
        project.SetCurrentTimeline(working_timeline)


def get_project_manager():
    from . import bmdvr
    if not self.project_manager:
        self.project_manager = bmdvr.GetProjectManager()
    return self.project_manager


def get_media_storage():
    from . import bmdvr
    if not self.media_storage:
        self.media_storage = bmdvr.GetMediaStorage()
    return self.media_storage


def get_current_project():
    # initialize project manager
    get_project_manager()

    return self.project_manager.GetCurrentProject()


def get_current_timeline(new=False):
    # get current project
    project = get_current_project()

    if new:
        media_pool = project.GetMediaPool()
        new_timeline = media_pool.CreateEmptyTimeline(self.pype_timeline_name)
        project.SetCurrentTimeline(new_timeline)

    return project.GetCurrentTimeline()


def create_bin(name: str, root: object = None) -> object:
    """
    Create media pool's folder.

    Return folder object and if the name does not exist it will create a new.
    If the input name is with forward or backward slashes then it will create
    all parents and return the last child bin object

    Args:
        name (str): name of folder / bin, or hierarchycal name "parent/name"
        root (resolve.Folder)[optional]: root folder / bin object

    Returns:
        object: resolve.Folder
    """
    # get all variables
    media_pool = get_current_project().GetMediaPool()
    root_bin = root or media_pool.GetRootFolder()

    # create hierarchy of bins in case there is slash in name
    if "/" in name.replace("\\", "/"):
        child_bin = None
        for bname in name.split("/"):
            child_bin = create_bin(bname, child_bin or root_bin)
        if child_bin:
            return child_bin
    else:
        created_bin = None
        for subfolder in root_bin.GetSubFolderList():
            if subfolder.GetName() in name:
                created_bin = subfolder

        if not created_bin:
            new_folder = media_pool.AddSubFolder(root_bin, name)
            media_pool.SetCurrentFolder(new_folder)
        else:
            media_pool.SetCurrentFolder(created_bin)

        return media_pool.GetCurrentFolder()


def create_media_pool_item(fpath: str,
                           root: object = None) -> object:
    """
    Create media pool item.

    Args:
        fpath (str): absolute path to a file
        root (resolve.Folder)[optional]: root folder / bin object

    Returns:
        object: resolve.MediaPoolItem
    """
    # get all variables
    media_storage = get_media_storage()
    media_pool = get_current_project().GetMediaPool()
    root_bin = root or media_pool.GetRootFolder()

    # try to search in bin if the clip does not exist
    existing_mpi = get_media_pool_item(fpath, root_bin)

    if existing_mpi:
        return existing_mpi

    dirname, file = os.path.split(fpath)
    _name, ext = os.path.splitext(file)

    # add all data in folder to mediapool
    media_pool_items = media_storage.AddItemListToMediaPool(
        os.path.normpath(dirname))

    if not media_pool_items:
        return False

    # if any are added then look into them for the right extension
    media_pool_item = [mpi for mpi in media_pool_items
                       if ext in mpi.GetClipProperty("File Path")]

    # return only first found
    return media_pool_item.pop()


def get_media_pool_item(fpath, root: object = None) -> object:
    """
    Return clip if found in folder with use of input file path.

    Args:
        fpath (str): absolute path to a file
        root (resolve.Folder)[optional]: root folder / bin object

    Returns:
        object: resolve.MediaPoolItem
    """
    media_pool = get_current_project().GetMediaPool()
    root = root or media_pool.GetRootFolder()
    fname = os.path.basename(fpath)

    for _mpi in root.GetClipList():
        _mpi_name = _mpi.GetClipProperty("File Name")
        _mpi_name = get_reformated_path(_mpi_name, first=True)
        if fname in _mpi_name:
            return _mpi
    return None


def create_timeline_item(media_pool_item: object,
                         timeline: object = None,
                         source_start: int = None,
                         source_end: int = None) -> object:
    """
    Add media pool item to current or defined timeline.

    Args:
        media_pool_item (resolve.MediaPoolItem): resolve's object
        timeline (resolve.Timeline)[optional]: resolve's object
        source_start (int)[optional]: media source input frame (sequence frame)
        source_end (int)[optional]: media source output frame (sequence frame)

    Returns:
        object: resolve.TimelineItem
    """
    # get all variables
    project = get_current_project()
    media_pool = project.GetMediaPool()
    _clip_property = media_pool_item.GetClipProperty
    clip_name = _clip_property("File Name")
    timeline = timeline or get_current_timeline()

    # if timeline was used then switch it to current timeline
    with maintain_current_timeline(timeline):
        # Add input mediaPoolItem to clip data
        clip_data = {"mediaPoolItem": media_pool_item}

        # add source time range if input was given
        if source_start is not None:
            clip_data.update({"startFrame": source_start})
        if source_end is not None:
            clip_data.update({"endFrame": source_end})

        print(clip_data)
        # add to timeline
        media_pool.AppendToTimeline([clip_data])

        output_timeline_item = get_timeline_item(
            media_pool_item, timeline)

    assert output_timeline_item, AssertionError(
        "Track Item with name `{}` doesnt exist on the timeline: `{}`".format(
            clip_name, timeline.GetName()
        ))
    return output_timeline_item


def get_timeline_item(media_pool_item: object,
                      timeline: object = None) -> object:
    """
    Returns clips related to input mediaPoolItem.

    Args:
        media_pool_item (resolve.MediaPoolItem): resolve's object
        timeline (resolve.Timeline)[optional]: resolve's object

    Returns:
        object: resolve.TimelineItem
    """
    _clip_property = media_pool_item.GetClipProperty
    clip_name = _clip_property("File Name")
    output_timeline_item = None
    timeline = timeline or get_current_timeline()

    with maintain_current_timeline(timeline):
        # search the timeline for the added clip

        for _ti_data in get_current_timeline_items():
            _ti_clip = _ti_data["clip"]["item"]
            _ti_clip_property = _ti_clip.GetMediaPoolItem().GetClipProperty
            if clip_name in _ti_clip_property("File Name"):
                output_timeline_item = _ti_clip

    return output_timeline_item


def get_video_track_names() -> list:
    tracks = list()
    track_type = "video"
    timeline = get_current_timeline()

    # get all tracks count filtered by track type
    selected_track_count = timeline.GetTrackCount(track_type)

    # loop all tracks and get items
    track_index: int
    for track_index in range(1, (int(selected_track_count) + 1)):
        track_name = timeline.GetTrackName("video", track_index)
        tracks.append(track_name)

    return tracks


def get_current_timeline_items(
        filter: bool = False,
        track_type: str = None,
        track_name: str = None,
        selecting_color: str = None) -> list:
    """ Gets all available current timeline track items
    """
    track_type = track_type or "video"
    selecting_color = selecting_color or "Chocolate"
    project = get_current_project()
    timeline = get_current_timeline()
    selected_clips = []

    # get all tracks count filtered by track type
    selected_track_count = timeline.GetTrackCount(track_type)

    # loop all tracks and get items
    _clips = dict()
    for track_index in range(1, (int(selected_track_count) + 1)):
        _track_name = timeline.GetTrackName(track_type, track_index)

        # filter out all unmathed track names
        if track_name:
            if _track_name not in track_name:
                continue

        timeline_items = timeline.GetItemListInTrack(
            track_type, track_index)
        _clips[track_index] = timeline_items

        _data = {
            "project": project,
            "timeline": timeline,
            "track": {
                "name": _track_name,
                "index": track_index,
                "type": track_type}
        }
        # get track item object and its color
        for clip_index, ti in enumerate(_clips[track_index]):
            data = _data.copy()
            data["clip"] = {
                "item": ti,
                "index": clip_index
            }
            ti_color = ti.GetClipColor()
            if filter is True:
                if selecting_color in ti_color:
                    selected_clips.append(data)
            else:
                selected_clips.append(data)

    return selected_clips


def get_pype_timeline_item_by_name(name: str) -> object:
    track_itmes = get_current_timeline_items()
    for _ti in track_itmes:
        tag_data = get_timeline_item_pype_tag(_ti["clip"]["item"])
        tag_name = tag_data.get("name")
        if not tag_name:
            continue
        if tag_data.get("name") in name:
            return _ti
    return None


def get_timeline_item_pype_tag(timeline_item):
    """
    Get openpype track item tag created by creator or loader plugin.

    Attributes:
        trackItem (resolve.TimelineItem): resolve object

    Returns:
        dict: openpype tag data
    """
    return_tag = None

    if self.pype_marker_workflow:
        return_tag = get_pype_marker(timeline_item)
    else:
        media_pool_item = timeline_item.GetMediaPoolItem()

        # get all tags from track item
        _tags = media_pool_item.GetMetadata()
        if not _tags:
            return None
        for key, data in _tags.items():
            # return only correct tag defined by global name
            if key in self.pype_tag_name:
                return_tag = json.loads(data)

    return return_tag


def set_timeline_item_pype_tag(timeline_item, data=None):
    """
    Set openpype track item tag to input timeline_item.

    Attributes:
        trackItem (resolve.TimelineItem): resolve api object

    Returns:
        dict: json loaded data
    """
    data = data or dict()

    # get available openpype tag if any
    tag_data = get_timeline_item_pype_tag(timeline_item)

    if self.pype_marker_workflow:
        # delete tag as it is not updatable
        if tag_data:
            delete_pype_marker(timeline_item)

        tag_data.update(data)
        set_pype_marker(timeline_item, tag_data)
    else:
        if tag_data:
            media_pool_item = timeline_item.GetMediaPoolItem()
            # it not tag then create one
            tag_data.update(data)
            media_pool_item.SetMetadata(
                self.pype_tag_name, json.dumps(tag_data))
        else:
            tag_data = data
            # if openpype tag available then update with input data
            # add it to the input track item
            timeline_item.SetMetadata(self.pype_tag_name, json.dumps(tag_data))

    return tag_data


def imprint(timeline_item, data=None):
    """
    Adding `Avalon data` into a hiero track item tag.

    Also including publish attribute into tag.

    Arguments:
        timeline_item (hiero.core.TrackItem): hiero track item object
        data (dict): Any data which needst to be imprinted

    Examples:
        data = {
            'asset': 'sq020sh0280',
            'family': 'render',
            'subset': 'subsetMain'
        }
    """
    data = data or {}

    set_timeline_item_pype_tag(timeline_item, data)

    # add publish attribute
    set_publish_attribute(timeline_item, True)


def set_publish_attribute(timeline_item, value):
    """ Set Publish attribute in input Tag object

    Attribute:
        tag (hiero.core.Tag): a tag object
        value (bool): True or False
    """
    tag_data = get_timeline_item_pype_tag(timeline_item)
    tag_data["publish"] = value
    # set data to the publish attribute
    set_timeline_item_pype_tag(timeline_item, tag_data)


def get_publish_attribute(timeline_item):
    """ Get Publish attribute from input Tag object

    Attribute:
        tag (hiero.core.Tag): a tag object
        value (bool): True or False
    """
    tag_data = get_timeline_item_pype_tag(timeline_item)
    return tag_data["publish"]


def set_pype_marker(timeline_item, tag_data):
    source_start = timeline_item.GetLeftOffset()
    item_duration = timeline_item.GetDuration()
    frame = int(source_start + (item_duration / 2))

    # marker attributes
    frameId = (frame / 10) * 10
    color = self.pype_marker_color
    name = self.pype_marker_name
    note = json.dumps(tag_data)
    duration = (self.pype_marker_duration / 10) * 10

    timeline_item.AddMarker(
        frameId,
        color,
        name,
        note,
        duration
    )


def get_pype_marker(timeline_item):
    timeline_item_markers = timeline_item.GetMarkers()
    for marker_frame in timeline_item_markers:
        note = timeline_item_markers[marker_frame]["note"]
        color = timeline_item_markers[marker_frame]["color"]
        name = timeline_item_markers[marker_frame]["name"]
        print(f"_ marker data: {marker_frame} | {name} | {color} | {note}")
        if name == self.pype_marker_name and color == self.pype_marker_color:
            self.temp_marker_frame = marker_frame
            return json.loads(note)

    return dict()


def delete_pype_marker(timeline_item):
    timeline_item.DeleteMarkerAtFrame(self.temp_marker_frame)
    self.temp_marker_frame = None


def create_compound_clip(clip_data, name, folder):
    """
    Convert timeline object into nested timeline object

    Args:
        clip_data (dict): timeline item object packed into dict
                          with project, timeline (sequence)
        folder (resolve.MediaPool.Folder): media pool folder object,
        name (str): name for compound clip

    Returns:
        resolve.MediaPoolItem: media pool item with compound clip timeline(cct)
    """
    # get basic objects form data
    project = clip_data["project"]
    timeline = clip_data["timeline"]
    clip = clip_data["clip"]

    # get details of objects
    clip_item = clip["item"]

    mp = project.GetMediaPool()

    # get clip attributes
    clip_attributes = get_clip_attributes(clip_item)

    mp_item = clip_item.GetMediaPoolItem()
    _mp_props = mp_item.GetClipProperty

    mp_first_frame = int(_mp_props("Start"))
    mp_last_frame = int(_mp_props("End"))

    # initialize basic source timing for otio
    ci_l_offset = clip_item.GetLeftOffset()
    ci_duration = clip_item.GetDuration()
    rate = float(_mp_props("FPS"))

    # source rational times
    mp_in_rc = opentime.RationalTime((ci_l_offset), rate)
    mp_out_rc = opentime.RationalTime((ci_l_offset + ci_duration - 1), rate)

    # get frame in and out for clip swapping
    in_frame = opentime.to_frames(mp_in_rc)
    out_frame = opentime.to_frames(mp_out_rc)

    # keep original sequence
    tl_origin = timeline

    # Set current folder to input media_pool_folder:
    mp.SetCurrentFolder(folder)

    # check if clip doesnt exist already:
    clips = folder.GetClipList()
    cct = next((c for c in clips
                if c.GetName() in name), None)

    if cct:
        print(f"_ cct exists: {cct}")
    else:
        # Create empty timeline in current folder and give name:
        cct = mp.CreateEmptyTimeline(name)

        # check if clip doesnt exist already:
        clips = folder.GetClipList()
        cct = next((c for c in clips
                    if c.GetName() in name), None)
        print(f"_ cct created: {cct}")

        with maintain_current_timeline(cct, tl_origin):
            # Add input clip to the current timeline:
            mp.AppendToTimeline([{
                "mediaPoolItem": mp_item,
                "startFrame": mp_first_frame,
                "endFrame": mp_last_frame
            }])

    # Add collected metadata and attributes to the comound clip:
    if mp_item.GetMetadata(self.pype_tag_name):
        clip_attributes[self.pype_tag_name] = mp_item.GetMetadata(
            self.pype_tag_name)[self.pype_tag_name]

    # stringify
    clip_attributes = json.dumps(clip_attributes)

    # add attributes to metadata
    for k, v in mp_item.GetMetadata().items():
        cct.SetMetadata(k, v)

    # add metadata to cct
    cct.SetMetadata(self.pype_tag_name, clip_attributes)

    # reset start timecode of the compound clip
    cct.SetClipProperty("Start TC", _mp_props("Start TC"))

    # swap clips on timeline
    swap_clips(clip_item, cct, in_frame, out_frame)

    cct.SetClipColor("Pink")
    return cct


def swap_clips(from_clip, to_clip, to_in_frame, to_out_frame):
    """
    Swapping clips on timeline in timelineItem

    It will add take and activate it to the frame range which is inputted

    Args:
        from_clip (resolve.TimelineItem)
        to_clip (resolve.mediaPoolItem)
        to_clip_name (str): name of to_clip
        to_in_frame (float): cut in frame, usually `GetLeftOffset()`
        to_out_frame (float): cut out frame, usually left offset plus duration

    Returns:
        bool: True if successfully replaced

    """
    _clip_prop = to_clip.GetClipProperty
    to_clip_name = _clip_prop("File Name")
    # add clip item as take to timeline
    take = from_clip.AddTake(
        to_clip,
        float(to_in_frame),
        float(to_out_frame)
    )

    if not take:
        return False

    for take_index in range(1, (int(from_clip.GetTakesCount()) + 1)):
        take_item = from_clip.GetTakeByIndex(take_index)
        take_mp_item = take_item["mediaPoolItem"]
        if to_clip_name in take_mp_item.GetName():
            from_clip.SelectTakeByIndex(take_index)
            from_clip.FinalizeTake()
            return True
    return False


def _validate_tc(x):
    # Validate and reformat timecode string

    if len(x) != 11:
        print('Invalid timecode. Try again.')

    c = ':'
    colonized = x[:2] + c + x[3:5] + c + x[6:8] + c + x[9:]

    if colonized.replace(':', '').isdigit():
        print(f"_ colonized: {colonized}")
        return colonized
    else:
        print('Invalid timecode. Try again.')


def get_pype_clip_metadata(clip):
    """
    Get openpype metadata created by creator plugin

    Attributes:
        clip (resolve.TimelineItem): resolve's object

    Returns:
        dict: hierarchy, orig clip attributes
    """
    mp_item = clip.GetMediaPoolItem()
    metadata = mp_item.GetMetadata()

    return metadata.get(self.pype_tag_name)


def get_clip_attributes(clip):
    """
    Collect basic attributes from resolve timeline item

    Args:
        clip (resolve.TimelineItem): timeline item object

    Returns:
        dict: all collected attributres as key: values
    """
    mp_item = clip.GetMediaPoolItem()

    return {
        "clipIn": clip.GetStart(),
        "clipOut": clip.GetEnd(),
        "clipLeftOffset": clip.GetLeftOffset(),
        "clipRightOffset": clip.GetRightOffset(),
        "clipMarkers": clip.GetMarkers(),
        "clipFlags": clip.GetFlagList(),
        "sourceId": mp_item.GetMediaId(),
        "sourceProperties": mp_item.GetClipProperty()
    }


def set_project_manager_to_folder_name(folder_name):
    """
    Sets context of Project manager to given folder by name.

    Searching for folder by given name from root folder to nested.
    If no existing folder by name it will create one in root folder.

    Args:
        folder_name (str): name of searched folder

    Returns:
        bool: True if success

    Raises:
        Exception: Cannot create folder in root

    """
    # initialize project manager
    get_project_manager()

    set_folder = False

    # go back to root folder
    if self.project_manager.GotoRootFolder():
        log.info(f"Testing existing folder: {folder_name}")
        folders = _convert_resolve_list_type(
            self.project_manager.GetFoldersInCurrentFolder())
        log.info(f"Testing existing folders: {folders}")
        # get me first available folder object
        # with the same name as in `folder_name` else return False
        if next((f for f in folders if f in folder_name), False):
            log.info(f"Found existing folder: {folder_name}")
            set_folder = self.project_manager.OpenFolder(folder_name)

    if set_folder:
        return True

    # if folder by name is not existent then create one
    # go back to root folder
    log.info(f"Folder `{folder_name}` not found and will be created")
    if self.project_manager.GotoRootFolder():
        try:
            # create folder by given name
            self.project_manager.CreateFolder(folder_name)
            self.project_manager.OpenFolder(folder_name)
            return True
        except NameError as e:
            log.error((f"Folder with name `{folder_name}` cannot be created!"
                       f"Error: {e}"))
            return False


def _convert_resolve_list_type(resolve_list):
    """ Resolve is using indexed dictionary as list type.
    `{1.0: 'vaule'}`
    This will convert it to normal list class
    """
    assert isinstance(resolve_list, dict), (
        "Input argument should be dict() type")

    return [resolve_list[i] for i in sorted(resolve_list.keys())]


def create_otio_time_range_from_timeline_item_data(timeline_item_data):
    timeline_item = timeline_item_data["clip"]["item"]
    project = timeline_item_data["project"]
    timeline = timeline_item_data["timeline"]
    timeline_start = timeline.GetStartFrame()

    frame_start = int(timeline_item.GetStart() - timeline_start)
    frame_duration = int(timeline_item.GetDuration())
    fps = project.GetSetting("timelineFrameRate")

    return otio_export.create_otio_time_range(
        frame_start, frame_duration, fps)


def get_otio_clip_instance_data(otio_timeline, timeline_item_data):
    """
    Return otio objects for timeline, track and clip

    Args:
        timeline_item_data (dict): timeline_item_data from list returned by
                                resolve.get_current_timeline_items()
        otio_timeline (otio.schema.Timeline): otio object

    Returns:
        dict: otio clip object

    """

    timeline_item = timeline_item_data["clip"]["item"]
    track_name = timeline_item_data["track"]["name"]
    timeline_range = create_otio_time_range_from_timeline_item_data(
        timeline_item_data)

    for otio_clip in otio_timeline.each_clip():
        track_name = otio_clip.parent().name
        parent_range = otio_clip.range_in_parent()
        if track_name not in track_name:
            continue
        if otio_clip.name not in timeline_item.GetName():
            continue
        if openpype.lib.is_overlapping_otio_ranges(
                parent_range, timeline_range, strict=True):

            # add pypedata marker to otio_clip metadata
            for marker in otio_clip.markers:
                if self.pype_marker_name in marker.name:
                    otio_clip.metadata.update(marker.metadata)
            return {"otioClip": otio_clip}

    return None


def get_reformated_path(path, padded=False, first=False):
    """
    Return fixed python expression path

    Args:
        path (str): path url or simple file name

    Returns:
        type: string with reformated path

    Example:
        get_reformated_path("plate.[0001-1008].exr") > plate.%04d.exr

    """
    first_frame_pattern = re.compile(r"\[(\d+)\-\d+\]")

    if "[" in path:
        padding_pattern = r"(\d+)(?=-)"
        padding = len(re.findall(padding_pattern, path).pop())
        num_pattern = r"(\[\d+\-\d+\])"
        if padded:
            path = re.sub(num_pattern, f"%0{padding}d", path)
        elif first:
            first_frame = re.findall(first_frame_pattern, path, flags=0)
            if len(first_frame) >= 1:
                first_frame = first_frame[0]
            path = re.sub(num_pattern, first_frame, path)
        else:
            path = re.sub(num_pattern, "%d", path)
    return path
