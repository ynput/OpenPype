"""
Host specific functions where host api is connected
"""
import os
import re
import sys
import ast
import hiero
import avalon.api as avalon
from avalon.vendor.Qt import QtWidgets
import pype.api as pype
from pype.api import Logger, Anatomy
from . import tags
# from opentimelineio import opentime
# from pprint import pformat

log = Logger().get_logger(__name__, "hiero")

self = sys.modules[__name__]
self._has_been_setup = False
self._has_menu = False
self._registered_gui = None
self.pype_tag_name = "Pype Data"
self.default_sequence_name = "PypeSequence"
self.default_bin_name = "PypeBin"

AVALON_CONFIG = os.getenv("AVALON_CONFIG", "pype")


def get_current_project():
    return next(iter(hiero.core.projects()))


def get_current_sequence(name=None, new=False):
    """
    Get current sequence in context of active project.

    Args:
        name (str)[optional]: name of sequence we want to return
        new (bool)[optional]: if we want to create new one

    Returns:
        hiero.core.Sequence: the sequence object
    """
    sequence = None
    project = get_current_project()
    root_bin = project.clipsBin()

    if new:
        # create new
        name = name or self.default_sequence_name
        sequence = hiero.core.Sequence(name)
        root_bin.addItem(hiero.core.BinItem(sequence))
    elif name:
        # look for sequence by name
        sequences = project.sequences()
        for _sequence in sequences:
            if _sequence.name() == name:
                sequence = _sequence
        if not sequence:
            # if nothing found create new with input name
            sequence = get_current_sequence(name, True)
    elif not name and not new:
        # if name is none and new is False then return current open sequence
        sequence = hiero.ui.activeSequence()

    return sequence


def get_current_track(sequence, name, audio=False):
    """
    Get current track in context of active project.

    Creates new if none is found.

    Args:
        sequence (hiero.core.Sequence): hiero sequene object
        name (str): name of track we want to return
        audio (bool)[optional]: switch to AudioTrack

    Returns:
        hiero.core.Track: the track object
    """
    tracks = sequence.videoTracks()

    if audio:
        tracks = sequence.audioTracks()

    # get track by name
    track = None
    for _track in tracks:
        if _track.name() in name:
            track = _track

    if not track:
        if audio:
            track = hiero.core.VideoTrack(name)
        else:
            track = hiero.core.AudioTrack(name)
        sequence.addTrack(track)

    return track


def get_track_items(
        selected=False,
        track_item_name=None,
        track_name=None,
        track_type=None,
        check_enabled=False,
        check_locked=False):
    """Get all available current timeline track items."""
    return_list = list()
    track_items = list()

    # get selected track items or all in active sequence
    if selected:
        selected_items = list(hiero.selection)
        for item in selected_items:
            if track_name and track_name in item.parent().name():
                # filter only items fitting input track name
                track_items.append(item)
            elif not track_name:
                # or add all if no track_name was defined
                track_items.append(item)
    else:
        # QUESTION: perhaps defining sequence will be needed for a automation
        sequence = get_current_sequence()
        # get all available tracks from sequence
        tracks = list(sequence.audioTracks()) + list(sequence.videoTracks())
        # loop all tracks
        for track in tracks:
            if check_locked and track.isLocked():
                continue
            # and all items in track
            for item in track.items():
                # check if track item is enabled
                if check_enabled:
                    if not item.isEnabled():
                        continue
                if track_item_name:
                    if item.name() in track_item_name:
                        return item
                # make sure only track items with correct track names are added
                if track_name and track_name in track.name():
                    # filter out only defined track_name items
                    track_items.append(item)
                elif not track_name:
                    # or add all if no track_name is defined
                    track_items.append(item)

    # filter out only track items with defined track_type
    for track_item in track_items:
        if track_type and track_type == "video" and isinstance(
                track_item.parent(), hiero.core.VideoTrack):
            # only video track items are allowed
            return_list.append(track_item)
        elif track_type and track_type == "audio" and isinstance(
                track_item.parent(), hiero.core.AudioTrack):
            # only audio track items are allowed
            return_list.append(track_item)
        elif not track_type:
            # add all if no track_type is defined
            return_list.append(track_item)

    return return_list


def get_track_item_pype_tag(track_item):
    """
    Get pype track item tag created by creator or loader plugin.

    Attributes:
        trackItem (hiero.core.TrackItem): hiero object

    Returns:
        hiero.core.Tag: hierarchy, orig clip attributes
    """
    # get all tags from track item
    _tags = track_item.tags()
    for tag in _tags:
        # return only correct tag defined by global name
        if tag.name() in self.pype_tag_name:
            return tag


def set_track_item_pype_tag(track_item, data=None):
    """
    Set pype track item tag to input track_item.

    Attributes:
        trackItem (hiero.core.TrackItem): hiero object

    Returns:
        hiero.core.Tag
    """
    data = data or dict()

    # basic Tag's attribute
    tag_data = {
        "editable": "0",
        "note": "Pype data holder",
        "icon": "pype_icon.png",
        "metadata": {k: v for k, v in data.items()}
    }
    # get available pype tag if any
    _tag = get_track_item_pype_tag(track_item)

    if _tag:
        # it not tag then create one
        tag = tags.update_tag(_tag, tag_data)
    else:
        # if pype tag available then update with input data
        tag = tags.create_tag(self.pype_tag_name, tag_data)
        # add it to the input track item
        track_item.addTag(tag)

    return tag


def get_track_item_pype_data(track_item):
    """
    Get track item's pype tag data.

    Attributes:
        trackItem (hiero.core.TrackItem): hiero object

    Returns:
        dict: data found on pype tag
    """
    data = dict()
    # get pype data tag from track item
    tag = get_track_item_pype_tag(track_item)
    # get tag metadata attribut
    tag_data = tag.metadata()
    # convert tag metadata to normal keys names and values to correct types
    for k, v in dict(tag_data).items():
        key = k.replace("tag.", "")

        try:
            # capture exceptions which are related to strings only
            value = ast.literal_eval(v)
        except (ValueError, SyntaxError):
            value = v

        data.update({key: value})

    return data


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

    tag = set_track_item_pype_tag(track_item, data)

    # add publish attribute
    set_publish_attribute(tag, True)


def set_publish_attribute(tag, value):
    """ Set Publish attribute in input Tag object

    Attribute:
        tag (hiero.core.Tag): a tag object
        value (bool): True or False
    """
    tag_data = tag.metadata()
    # set data to the publish attribute
    tag_data.setValue("tag.publish", str(value))


def get_publish_attribute(tag):
    """ Get Publish attribute from input Tag object

    Attribute:
        tag (hiero.core.Tag): a tag object
        value (bool): True or False
    """
    tag_data = tag.metadata()
    # get data to the publish attribute
    value = tag_data.value("tag.publish")
    # return value converted to bool value. Atring is stored in tag.
    return ast.literal_eval(value)


def sync_avalon_data_to_workfile():
    # import session to get project dir
    project_name = avalon.Session["AVALON_PROJECT"]

    anatomy = Anatomy(project_name)
    work_template = anatomy.templates["work"]["path"]
    work_root = anatomy.root_value_for_template(work_template)
    active_project_root = (
        os.path.join(work_root, project_name)
    ).replace("\\", "/")
    # getting project
    project = get_current_project()

    if "Tag Presets" in project.name():
        return

    log.debug("Synchronizing Pype metadata to project: {}".format(
        project.name()))

    # set project root with backward compatibility
    try:
        project.setProjectDirectory(active_project_root)
    except Exception:
        # old way of seting it
        project.setProjectRoot(active_project_root)

    # get project data from avalon db
    project_data = pype.get_project()["data"]

    log.debug("project_data: {}".format(project_data))

    # get format and fps property from avalon db on project
    width = project_data["resolutionWidth"]
    height = project_data["resolutionHeight"]
    pixel_aspect = project_data["pixelAspect"]
    fps = project_data['fps']
    format_name = project_data['code']

    # create new format in hiero project
    format = hiero.core.Format(width, height, pixel_aspect, format_name)
    project.setOutputFormat(format)

    # set fps to hiero project
    project.setFramerate(fps)

    # TODO: add auto colorspace set from project drop
    log.info("Project property has been synchronised with Avalon db")


def launch_workfiles_app(event):
    """
    Event for launching workfiles after hiero start

    Args:
        event (obj): required but unused
    """
    from . import launch_workfiles_app
    launch_workfiles_app()


def setup(console=False, port=None, menu=True):
    """Setup integration

    Registers Pyblish for Hiero plug-ins and appends an item to the File-menu

    Arguments:
        console (bool): Display console with GUI
        port (int, optional): Port from which to start looking for an
            available port to connect with Pyblish QML, default
            provided by Pyblish Integration.
        menu (bool, optional): Display file menu in Hiero.
    """

    if self._has_been_setup:
        teardown()

    add_submission()

    if menu:
        add_to_filemenu()
        self._has_menu = True

    self._has_been_setup = True
    log.debug("pyblish: Loaded successfully.")


def teardown():
    """Remove integration"""
    if not self._has_been_setup:
        return

    if self._has_menu:
        remove_from_filemenu()
        self._has_menu = False

    self._has_been_setup = False
    log.debug("pyblish: Integration torn down successfully")


def remove_from_filemenu():
    raise NotImplementedError("Implement me please.")


def add_to_filemenu():
    PublishAction()


class PyblishSubmission(hiero.exporters.FnSubmission.Submission):

    def __init__(self):
        hiero.exporters.FnSubmission.Submission.__init__(self)

    def addToQueue(self):
        from . import publish
        # Add submission to Hiero module for retrieval in plugins.
        hiero.submission = self
        publish()


def add_submission():
    registry = hiero.core.taskRegistry
    registry.addSubmission("Pyblish", PyblishSubmission)


class PublishAction(QtWidgets.QAction):
    """
    Action with is showing as menu item
    """

    def __init__(self):
        QtWidgets.QAction.__init__(self, "Publish", None)
        self.triggered.connect(self.publish)

        for interest in ["kShowContextMenu/kTimeline",
                         "kShowContextMenukBin",
                         "kShowContextMenu/kSpreadsheet"]:
            hiero.core.events.registerInterest(interest, self.eventHandler)

        self.setShortcut("Ctrl+Alt+P")

    def publish(self):
        from . import publish
        # Removing "submission" attribute from hiero module, to prevent tasks
        # from getting picked up when not using the "Export" dialog.
        if hasattr(hiero, "submission"):
            del hiero.submission
        publish()

    def eventHandler(self, event):
        # Add the Menu to the right-click menu
        event.menu.addAction(self)


# def CreateNukeWorkfile(nodes=None,
#                        nodes_effects=None,
#                        to_timeline=False,
#                        **kwargs):
#     ''' Creating nuke workfile with particular version with given nodes
#     Also it is creating timeline track items as precomps.
#
#     Arguments:
#         nodes(list of dict): each key in dict is knob order is important
#         to_timeline(type): will build trackItem with metadata
#
#     Returns:
#         bool: True if done
#
#     Raises:
#         Exception: with traceback
#
#     '''
#     import hiero.core
#     from avalon.nuke import imprint
#     from pype.hosts.nuke import (
#         lib as nklib
#         )
#
#     # check if the file exists if does then Raise "File exists!"
#     if os.path.exists(filepath):
#         raise FileExistsError("File already exists: `{}`".format(filepath))
#
#     # if no representations matching then
#     #   Raise "no representations to be build"
#     if len(representations) == 0:
#         raise AttributeError("Missing list of `representations`")
#
#     # check nodes input
#     if len(nodes) == 0:
#         log.warning("Missing list of `nodes`")
#
#     # create temp nk file
#     nuke_script = hiero.core.nuke.ScriptWriter()
#
#     # create root node and save all metadata
#     root_node = hiero.core.nuke.RootNode()
#
#     anatomy = Anatomy(os.environ["AVALON_PROJECT"])
#     work_template = anatomy.templates["work"]["path"]
#     root_path = anatomy.root_value_for_template(work_template)
#
#     nuke_script.addNode(root_node)
#
#     # here to call pype.hosts.nuke.lib.BuildWorkfile
#     script_builder = nklib.BuildWorkfile(
#         root_node=root_node,
#         root_path=root_path,
#         nodes=nuke_script.getNodes(),
#         **kwargs
#     )


def create_nuke_workfile_clips(nuke_workfiles, seq=None):
    '''
    nuke_workfiles is list of dictionaries like:
    [{
        'path': 'P:/Jakub_testy_pipeline/test_v01.nk',
        'name': 'test',
        'handleStart': 15, # added asymetrically to handles
        'handleEnd': 10, # added asymetrically to handles
        "clipIn": 16,
        "frameStart": 991,
        "frameEnd": 1023,
        'task': 'Comp-tracking',
        'work_dir': 'VFX_PR',
        'shot': '00010'
    }]
    '''

    proj = hiero.core.projects()[-1]
    root = proj.clipsBin()

    if not seq:
        seq = hiero.core.Sequence('NewSequences')
        root.addItem(hiero.core.BinItem(seq))
    # todo will ned to define this better
    # track = seq[1]  # lazy example to get a destination#  track
    clips_lst = []
    for nk in nuke_workfiles:
        task_path = '/'.join([nk['work_dir'], nk['shot'], nk['task']])
        bin = create_bin(task_path, proj)

        if nk['task'] not in seq.videoTracks():
            track = hiero.core.VideoTrack(nk['task'])
            seq.addTrack(track)
        else:
            track = seq.tracks(nk['task'])

        # create clip media
        media = hiero.core.MediaSource(nk['path'])
        media_in = int(media.startTime() or 0)
        media_duration = int(media.duration() or 0)

        handle_start = nk.get("handleStart")
        handle_end = nk.get("handleEnd")

        if media_in:
            source_in = media_in + handle_start
        else:
            source_in = nk["frameStart"] + handle_start

        if media_duration:
            source_out = (media_in + media_duration - 1) - handle_end
        else:
            source_out = nk["frameEnd"] - handle_end

        source = hiero.core.Clip(media)

        name = os.path.basename(os.path.splitext(nk['path'])[0])
        split_name = split_by_client_version(name)[0] or name

        # add to bin as clip item
        items_in_bin = [b.name() for b in bin.items()]
        if split_name not in items_in_bin:
            binItem = hiero.core.BinItem(source)
            bin.addItem(binItem)

        new_source = [
            item for item in bin.items() if split_name in item.name()
        ][0].items()[0].item()

        # add to track as clip item
        trackItem = hiero.core.TrackItem(
            split_name, hiero.core.TrackItem.kVideo)
        trackItem.setSource(new_source)
        trackItem.setSourceIn(source_in)
        trackItem.setSourceOut(source_out)
        trackItem.setTimelineIn(nk["clipIn"])
        trackItem.setTimelineOut(nk["clipIn"] + (source_out - source_in))
        track.addTrackItem(trackItem)
        clips_lst.append(trackItem)

    return clips_lst


def create_bin(path=None, project=None):
    '''
    Create bin in project.
    If the path is "bin1/bin2/bin3" it will create whole depth
    and return `bin3`

    '''
    # get the first loaded project
    project = project or get_current_project()

    path = path or self.default_bin_name

    path = path.replace("\\", "/").split("/")

    root_bin = project.clipsBin()

    done_bin_lst = []
    for i, b in enumerate(path):
        if i == 0 and len(path) > 1:
            if b in [bin.name() for bin in root_bin.bins()]:
                bin = [bin for bin in root_bin.bins() if b in bin.name()][0]
                done_bin_lst.append(bin)
            else:
                create_bin = hiero.core.Bin(b)
                root_bin.addItem(create_bin)
                done_bin_lst.append(create_bin)

        elif i >= 1 and i < len(path) - 1:
            if b in [bin.name() for bin in done_bin_lst[i - 1].bins()]:
                bin = [
                    bin for bin in done_bin_lst[i - 1].bins()
                    if b in bin.name()
                ][0]
                done_bin_lst.append(bin)
            else:
                create_bin = hiero.core.Bin(b)
                done_bin_lst[i - 1].addItem(create_bin)
                done_bin_lst.append(create_bin)

        elif i == len(path) - 1:
            if b in [bin.name() for bin in done_bin_lst[i - 1].bins()]:
                bin = [
                    bin for bin in done_bin_lst[i - 1].bins()
                    if b in bin.name()
                ][0]
                done_bin_lst.append(bin)
            else:
                create_bin = hiero.core.Bin(b)
                done_bin_lst[i - 1].addItem(create_bin)
                done_bin_lst.append(create_bin)

    return done_bin_lst[-1]


def split_by_client_version(string):
    regex = r"[/_.]v\d+"
    try:
        matches = re.findall(regex, string, re.IGNORECASE)
        return string.split(matches[0])
    except Exception as error:
        log.error(error)
        return None


def get_selected_track_items(sequence=None):
    _sequence = sequence or get_current_sequence()

    # Getting selection
    timeline_editor = hiero.ui.getTimelineEditor(_sequence)
    return timeline_editor.selection()


def set_selected_track_items(track_items_list, sequence=None):
    _sequence = sequence or get_current_sequence()

    # Getting selection
    timeline_editor = hiero.ui.getTimelineEditor(_sequence)
    return timeline_editor.setSelection(track_items_list)
