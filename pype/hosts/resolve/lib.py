import sys
import json
import ast
from opentimelineio import opentime
from pype.api import Logger

log = Logger().get_logger(__name__, "resolve")

self = sys.modules[__name__]
self.project_manager = None

# Pype sequencial rename variables
self.rename_index = 0
self.rename_add = 0

self.publish_clip_color = "Pink"
self.pype_marker_workflow = True

# Pype compound clip workflow variable
self.pype_tag_name = "VFX Notes"

# Pype marker workflow variables
self.pype_marker_name = "PYPEDATA"
self.pype_marker_duration = 1
self.pype_marker_color = "Mint"
self.temp_marker_frame = None

def get_project_manager():
    from . import bmdvr
    if not self.project_manager:
        self.project_manager = bmdvr.GetProjectManager()
    return self.project_manager


def get_current_project():
    # initialize project manager
    get_project_manager()

    return self.project_manager.GetCurrentProject()


def get_current_sequence():
    # get current project
    project = get_current_project()

    return project.GetCurrentTimeline()


def get_video_track_names():
    tracks = list()
    track_type = "video"
    sequence = get_current_sequence()

    # get all tracks count filtered by track type
    selected_track_count = sequence.GetTrackCount(track_type)

    # loop all tracks and get items
    for track_index in range(1, (int(selected_track_count) + 1)):
        track_name = sequence.GetTrackName("video", track_index)
        tracks.append(track_name)

    return tracks


def get_current_track_items(
        filter=False,
        track_type=None,
        selecting_color=None):
    """ Gets all available current timeline track items
    """
    track_type = track_type or "video"
    selecting_color = selecting_color or "Chocolate"
    project = get_current_project()
    sequence = get_current_sequence()
    selected_clips = list()

    # get all tracks count filtered by track type
    selected_track_count = sequence.GetTrackCount(track_type)

    # loop all tracks and get items
    _clips = dict()
    for track_index in range(1, (int(selected_track_count) + 1)):
        track_name = sequence.GetTrackName(track_type, track_index)
        track_track_items = sequence.GetItemListInTrack(
            track_type, track_index)
        _clips[track_index] = track_track_items

        _data = {
            "project": project,
            "sequence": sequence,
            "track": {
                "name": track_name,
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


def get_track_item_pype_tag(track_item):
    """
    Get pype track item tag created by creator or loader plugin.

    Attributes:
        trackItem (resolve.TimelineItem): hiero object

    Returns:
        hiero.core.Tag: hierarchy, orig clip attributes
    """
    return_tag = None

    if self.pype_marker_workflow:
        return_tag = get_pype_marker(track_item)
    else:
        media_pool_item = track_item.GetMediaPoolItem()

        # get all tags from track item
        _tags = media_pool_item.GetMetadata()
        if not _tags:
            return None
        for key, data in _tags.items():
            # return only correct tag defined by global name
            if key in self.pype_tag_name:
                return_tag = json.loads(data)

    return return_tag


def set_track_item_pype_tag(track_item, data=None):
    """
    Set pype track item tag to input track_item.

    Attributes:
        trackItem (resolve.TimelineItem): resolve api object

    Returns:
        dict: json loaded data
    """
    data = data or dict()

    # get available pype tag if any
    tag_data = get_track_item_pype_tag(track_item)

    if self.pype_marker_workflow:
        # delete tag as it is not updatable
        if tag_data:
            delete_pype_marker(track_item)

        tag_data.update(data)
        set_pype_marker(track_item, tag_data)
    else:
        if tag_data:
            media_pool_item = track_item.GetMediaPoolItem()
            # it not tag then create one
            tag_data.update(data)
            media_pool_item.SetMetadata(
                self.pype_tag_name, json.dumps(tag_data))
        else:
            tag_data = data
            # if pype tag available then update with input data
            # add it to the input track item
            track_item.SetMetadata(self.pype_tag_name, json.dumps(tag_data))

    return tag_data


def imprint(track_item, data=None):
    """
    Adding `Avalon data` into a hiero track item tag.

    Also including publish attribute into tag.

    Arguments:
        track_item (hiero.core.TrackItem): hiero track item object
        data (dict): Any data which needst to be imprinted

    Examples:
        data = {
            'asset': 'sq020sh0280',
            'family': 'render',
            'subset': 'subsetMain'
        }
    """
    data = data or {}

    set_track_item_pype_tag(track_item, data)

    # add publish attribute
    set_publish_attribute(track_item, True)


def set_publish_attribute(track_item, value):
    """ Set Publish attribute in input Tag object

    Attribute:
        tag (hiero.core.Tag): a tag object
        value (bool): True or False
    """
    tag_data = get_track_item_pype_tag(track_item)
    tag_data["publish"] = value
    # set data to the publish attribute
    set_track_item_pype_tag(track_item, tag_data)


def get_publish_attribute(track_item):
    """ Get Publish attribute from input Tag object

    Attribute:
        tag (hiero.core.Tag): a tag object
        value (bool): True or False
    """
    tag_data = get_track_item_pype_tag(track_item)
    return tag_data["publish"]


def set_pype_marker(track_item, tag_data):
    source_start = track_item.GetLeftOffset()
    item_duration = track_item.GetDuration()
    frame = int(source_start + (item_duration / 2))

    # marker attributes
    frameId = (frame / 10) * 10
    color = self.pype_marker_color
    name = self.pype_marker_name
    note = json.dumps(tag_data)
    duration = (self.pype_marker_duration / 10) * 10

    track_item.AddMarker(
        frameId,
        color,
        name,
        note,
        duration
    )


def get_pype_marker(track_item):
    track_item_markers = track_item.GetMarkers()
    for marker_frame in track_item_markers:
        note = track_item_markers[marker_frame]["note"]
        color = track_item_markers[marker_frame]["color"]
        name = track_item_markers[marker_frame]["name"]
        print(f"_ marker data: {marker_frame} | {name} | {color} | {note}")
        if name == self.pype_marker_name and color == self.pype_marker_color:
            self.temp_marker_frame = marker_frame
            return json.loads(note)

    return dict()


def delete_pype_marker(track_item):
    track_item.DeleteMarkerAtFrame(self.temp_marker_frame)
    self.temp_marker_frame = None


def create_current_sequence_media_bin(sequence):
    seq_name = sequence.GetName()
    media_pool = get_current_project().GetMediaPool()
    root_folder = media_pool.GetRootFolder()
    sub_folders = root_folder.GetSubFolderList()
    testing_names = list()

    print(f"_ sub_folders: {sub_folders}")
    for subfolder in sub_folders:
        subf_name = subfolder.GetName()
        if seq_name in subf_name:
            testing_names.append(subfolder)
        else:
            testing_names.append(False)

    matching = next((f for f in testing_names if f is not False), None)

    if not matching:
        new_folder = media_pool.AddSubFolder(root_folder, seq_name)
        media_pool.SetCurrentFolder(new_folder)
    else:
        media_pool.SetCurrentFolder(matching)

    return media_pool.GetCurrentFolder()


def get_name_with_data(clip_data, presets):
    """
    Take hierarchy data from presets and build name with parents data

    Args:
        clip_data (dict): clip data from `get_current_track_items()`
        presets (dict): data from create plugin

    Returns:
        list: name, data

    """
    def _replace_hash_to_expression(name, text):
        _spl = text.split("#")
        _len = (len(_spl) - 1)
        _repl = f"{{{name}:0>{_len}}}"
        new_text = text.replace(("#" * _len), _repl)
        return new_text

    # presets data
    clip_name = presets["clipName"]
    hierarchy = presets["hierarchy"]
    hierarchy_data = presets["hierarchyData"].copy()
    count_from = presets["countFrom"]
    steps = presets["steps"]

    # reset rename_add
    if self.rename_add < count_from:
        self.rename_add = count_from

    # shot num calculate
    if self.rename_index == 0:
        shot_num = self.rename_add
    else:
        shot_num = self.rename_add + steps

    print(f"shot_num: {shot_num}")

    # clip data
    _data = {
        "sequence": clip_data["sequence"].GetName(),
        "track": clip_data["track"]["name"].replace(" ", "_"),
        "shot": shot_num
    }

    # solve # in test to pythonic explression
    for k, v in hierarchy_data.items():
        if "#" not in v:
            continue
        hierarchy_data[k] = _replace_hash_to_expression(k, v)

    # fill up pythonic expresisons
    for k, v in hierarchy_data.items():
        hierarchy_data[k] = v.format(**_data)

    # fill up clip name and hierarchy keys
    hierarchy = hierarchy.format(**hierarchy_data)
    clip_name = clip_name.format(**hierarchy_data)

    self.rename_add = shot_num
    print(f"shot_num: {shot_num}")

    return (clip_name, {
        "hierarchy": hierarchy,
        "hierarchyData": hierarchy_data
    })


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
    sequence = clip_data["sequence"]
    clip = clip_data["clip"]

    # get details of objects
    clip_item = clip["item"]

    mp = project.GetMediaPool()

    # get clip attributes
    clip_attributes = get_clip_attributes(clip_item)

    mp_item = clip_item.GetMediaPoolItem()
    mp_props = mp_item.GetClipProperty()

    mp_first_frame = int(mp_props["Start"])
    mp_last_frame = int(mp_props["End"])

    # initialize basic source timing for otio
    ci_l_offset = clip_item.GetLeftOffset()
    ci_duration = clip_item.GetDuration()
    rate = float(mp_props["FPS"])

    # source rational times
    mp_in_rc = opentime.RationalTime((ci_l_offset), rate)
    mp_out_rc = opentime.RationalTime((ci_l_offset + ci_duration - 1), rate)

    # get frame in and out for clip swaping
    in_frame = opentime.to_frames(mp_in_rc)
    out_frame = opentime.to_frames(mp_out_rc)

    # keep original sequence
    sq_origin = sequence

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

        # Set current timeline to created timeline:
        project.SetCurrentTimeline(cct)

        # Add input clip to the current timeline:
        mp.AppendToTimeline([{
            "mediaPoolItem": mp_item,
            "startFrame": mp_first_frame,
            "endFrame": mp_last_frame
        }])

        # Set current timeline to the working timeline:
        project.SetCurrentTimeline(sq_origin)

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
    cct.SetClipProperty("Start TC", mp_props["Start TC"])

    # swap clips on timeline
    swap_clips(clip_item, cct, name, in_frame, out_frame)

    cct.SetClipColor("Pink")
    return cct


def swap_clips(from_clip, to_clip, to_clip_name, to_in_frame, to_out_frame):
    """
    Swaping clips on timeline in timelineItem

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


def validate_tc(x):
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
    Get pype metadata created by creator plugin

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
    Collect basic atrributes from resolve timeline item

    Args:
        clip (resolve.TimelineItem): timeline item object

    Returns:
        dict: all collected attributres as key: values
    """
    mp_item = clip.GetMediaPoolItem()

    data = {
        "clipIn": clip.GetStart(),
        "clipOut": clip.GetEnd(),
        "clipLeftOffset": clip.GetLeftOffset(),
        "clipRightOffset": clip.GetRightOffset(),
        "clipMarkers": clip.GetMarkers(),
        "clipFlags": clip.GetFlagList(),
        "sourceId": mp_item.GetMediaId(),
        "sourceProperties": mp_item.GetClipProperty()
    }
    return data


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
        folders = convert_resolve_list_type(
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


def convert_resolve_list_type(resolve_list):
    """ Resolve is using indexed dictionary as list type.
    `{1.0: 'vaule'}`
    This will convert it to normal list class
    """
    assert isinstance(resolve_list, dict), (
        "Input argument should be dict() type")

    return [resolve_list[i] for i in sorted(resolve_list.keys())]
