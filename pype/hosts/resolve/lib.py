import sys
import json
from pype.api import Logger

log = Logger().get_logger(__name__, "resolve")

self = sys.modules[__name__]
self.pm = None


def get_project_manager():
    from . import bmdvr
    if not self.pm:
        self.pm = bmdvr.GetProjectManager()
    return self.pm


def get_current_project():
    # initialize project manager
    get_project_manager()

    return self.pm.GetCurrentProject()


def get_current_sequence():
    # get current project
    project = get_current_project()

    return project.GetCurrentTimeline()


def get_current_track_items(
        filter=False,
        track_type=None,
        selecting_color=None):
    """ Gets all available current timeline track items
    """
    from pprint import pformat
    track_type = track_type or "video"
    selecting_color = selecting_color or "Chocolate"
    project = get_current_project()
    sequence = get_current_sequence()
    selected_clips = list()

    # get all tracks count filtered by track type
    sequence_video_count = sequence.GetTrackCount(track_type)

    # loop all tracks and get items
    _clips = dict()
    for track_index in range(1, (int(sequence_video_count) + 1)):
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
                    ti.ClearClipColor()
            else:
                selected_clips.append(data)

    return selected_clips


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


def create_compound_clip(clip_data, folder, presets):
    """
    Convert timeline object into nested timeline object

    Args:
        clip_data (dict): timeline item object packed into dict
                          with project, timeline (sequence)
        folder (resolve.MediaPool.Folder): media pool folder object,
        presets (dict): pype config plugin presets

    Returns:
        resolve.MediaPoolItem: media pool item with compound clip timeline(cct)
    """
    from pprint import pformat

    # get basic objects form data
    project = clip_data["project"]
    sequence = clip_data["sequence"]
    clip = clip_data["clip"]

    # get details of objects
    clip_item = clip["item"]
    track = clip_data["track"]

    # build name
    clip_name_split = clip_item.GetName().split(".")
    name = "_".join([
        track["name"],
        str(track["index"]),
        clip_name_split[0],
        str(clip["index"])]
    )

    # get metadata
    mp_item = clip_item.GetMediaPoolItem()
    mp_props = mp_item.GetClipProperty()
    clip_attributes = get_clip_attributes(clip_item)
    mp = project.GetMediaPool()

    # keep original sequence
    sq_origin = sequence

    print(f"_ sequence: {sequence}")
    print(f"_ metadata: {pformat(clip_attributes)}")

    # Set current folder to input media_pool_folder:
    mp.SetCurrentFolder(folder)

    # check if clip doesnt exist already:
    clips = folder.GetClipList()
    cct = next((c for c in clips
                if c.GetName() in name), None)

    if cct:
        print(f"_ cct exists: {cct}")
        return cct

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
    # TODO: set offsets if handles
    done = mp.AppendToTimeline([{
        "mediaPoolItem": mp_item,
        "startFrame": int(mp_props["Start"]),
        "endFrame": int(mp_props["End"])
    }])
    print(f"_ done1: {done}")

    # Set current timeline to the working timeline:
    project.SetCurrentTimeline(sq_origin)

    # Add collected metadata and attributes to the comound clip:
    clip_attributes["VFX Notes"] = mp_item.GetMetadata(
        "VFX Notes")["VFX Notes"]
    clip_attributes = json.dumps(clip_attributes)

    for k, v in mp_item.GetMetadata().items():
        done = cct.SetMetadata(k, v)

    done = cct.SetMetadata("VFX Notes", clip_attributes)
    print(f"_ done2: {done}")

    # # add clip item as take to timeline
    # AddTake(cct, startFrame, endFrame)
    return cct


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
    if self.pm.GotoRootFolder():
        log.info(f"Testing existing folder: {folder_name}")
        folders = convert_resolve_list_type(
            self.pm.GetFoldersInCurrentFolder())
        log.info(f"Testing existing folders: {folders}")
        # get me first available folder object
        # with the same name as in `folder_name` else return False
        if next((f for f in folders if f in folder_name), False):
            log.info(f"Found existing folder: {folder_name}")
            set_folder = self.pm.OpenFolder(folder_name)

    if set_folder:
        return True

    # if folder by name is not existent then create one
    # go back to root folder
    log.info(f"Folder `{folder_name}` not found and will be created")
    if self.pm.GotoRootFolder():
        try:
            # create folder by given name
            self.pm.CreateFolder(folder_name)
            self.pm.OpenFolder(folder_name)
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
