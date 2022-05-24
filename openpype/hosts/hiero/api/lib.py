"""
Host specific functions where host api is connected
"""

import contextlib
from copy import deepcopy
import os
import re
import sys
import platform
import ast
import shutil
import hiero

from Qt import QtWidgets
from bson.objectid import ObjectId

from openpype.pipeline import legacy_io
from openpype.api import (Logger, Anatomy, get_anatomy_settings)
from . import tags

try:
    from PySide.QtCore import QFile, QTextStream
    from PySide.QtXml import QDomDocument
except ImportError:
    from PySide2.QtCore import QFile, QTextStream
    from PySide2.QtXml import QDomDocument

# from opentimelineio import opentime
# from pprint import pformat

log = Logger().get_logger(__name__)

self = sys.modules[__name__]
self._has_been_setup = False
self._has_menu = False
self._registered_gui = None
self._parent = None
self.pype_tag_name = "openpypeData"
self.default_sequence_name = "openpypeSequence"
self.default_bin_name = "openpypeBin"


def flatten(_list):
    for item in _list:
        if isinstance(item, (list, tuple)):
            for sub_item in flatten(item):
                yield sub_item
        else:
            yield item


def get_current_project(remove_untitled=False):
    projects = flatten(hiero.core.projects())
    if not remove_untitled:
        return next(iter(projects))

    # if remove_untitled
    for proj in projects:
        if "Untitled" in proj.name():
            proj.close()
        else:
            return proj


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
    else:
        # if name is none and new is False then return current open sequence
        sequence = hiero.ui.activeSequence()

    return sequence


def get_timeline_selection():
    active_sequence = hiero.ui.activeSequence()
    timeline_editor = hiero.ui.getTimelineEditor(active_sequence)
    return list(timeline_editor.selection())


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
        if _track.name() == name:
            track = _track

    if not track:
        if not audio:
            track = hiero.core.VideoTrack(name)
        else:
            track = hiero.core.AudioTrack(name)

        sequence.addTrack(track)

    return track


def get_track_items(
        selection=False,
        sequence_name=None,
        track_item_name=None,
        track_name=None,
        track_type=None,
        check_enabled=True,
        check_locked=True,
        check_tagged=False):
    """Get all available current timeline track items.

    Attribute:
        selection (list)[optional]: list of selected track items
        sequence_name (str)[optional]: return only clips from input sequence
        track_item_name (str)[optional]: return only item with input name
        track_name (str)[optional]: return only items from track name
        track_type (str)[optional]: return only items of given type
                                    (`audio` or `video`) default is `video`
        check_enabled (bool)[optional]: ignore disabled if True
        check_locked (bool)[optional]: ignore locked if True

    Return:
        list or hiero.core.TrackItem: list of track items or single track item
    """
    track_type = track_type or "video"
    selection = selection or []
    return_list = []

    # get selected track items or all in active sequence
    if selection:
        with contextlib.suppress(AttributeError):
            for track_item in selection:
                log.info("___ track_item: {}".format(track_item))
                # make sure only trackitems are selected
                if not isinstance(track_item, hiero.core.TrackItem):
                    continue

                if _validate_all_atrributes(
                    track_item,
                    track_item_name,
                    track_name,
                    track_type,
                    check_enabled,
                    check_tagged
                ):
                    log.info("___ valid trackitem: {}".format(track_item))
                    return_list.append(track_item)

    # collect all available active sequence track items
    if not return_list:
        sequence = get_current_sequence(name=sequence_name)
        # get all available tracks from sequence
        tracks = list(sequence.audioTracks()) + list(sequence.videoTracks())
        # loop all tracks
        for track in tracks:
            if check_locked and track.isLocked():
                continue
            if check_enabled and not track.isEnabled():
                continue
            # and all items in track
            for track_item in track.items():
                # make sure no subtrackitem is also track items
                if not isinstance(track_item, hiero.core.TrackItem):
                    continue

                if _validate_all_atrributes(
                    track_item,
                    track_item_name,
                    track_name,
                    track_type,
                    check_enabled,
                    check_tagged
                ):
                    return_list.append(track_item)

    return return_list


def _validate_all_atrributes(
    track_item,
    track_item_name,
    track_name,
    track_type,
    check_enabled,
    check_tagged
):
    def _validate_correct_name_track_item():
        if track_item_name and track_item_name in track_item.name():
            return True
        elif not track_item_name:
            return True

    def _validate_tagged_track_item():
        if check_tagged and track_item.tags():
            return True
        elif not check_tagged:
            return True

    def _validate_enabled_track_item():
        if check_enabled and track_item.isEnabled():
            return True
        elif not check_enabled:
            return True

    def _validate_parent_track_item():
        if track_name and track_name in track_item.parent().name():
            # filter only items fitting input track name
            return True
        elif not track_name:
            # or add all if no track_name was defined
            return True

    def _validate_type_track_item():
        if track_type == "video" and isinstance(
                track_item.parent(), hiero.core.VideoTrack):
            # only video track items are allowed
            return True
        elif track_type == "audio" and isinstance(
                track_item.parent(), hiero.core.AudioTrack):
            # only audio track items are allowed
            return True

    # check if track item is enabled
    return all([
        _validate_enabled_track_item(),
        _validate_type_track_item(),
        _validate_tagged_track_item(),
        _validate_parent_track_item(),
        _validate_correct_name_track_item()
    ])


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
    if not _tags:
        return None
    for tag in _tags:
        # return only correct tag defined by global name
        if tag.name() == self.pype_tag_name:
            return tag


def set_track_item_pype_tag(track_item, data=None):
    """
    Set pype track item tag to input track_item.

    Attributes:
        trackItem (hiero.core.TrackItem): hiero object

    Returns:
        hiero.core.Tag
    """
    data = data or {}

    # basic Tag's attribute
    tag_data = {
        "editable": "0",
        "note": "OpenPype data container",
        "icon": "openpype_icon.png",
        "metadata": dict(data.items())
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
    data = {}
    # get pype data tag from track item
    tag = get_track_item_pype_tag(track_item)

    if not tag:
        return None

    # get tag metadata attribute
    tag_data = deepcopy(dict(tag.metadata()))
    # convert tag metadata to normal keys names and values to correct types
    for k, v in tag_data.items():
        key = k.replace("tag.", "")

        try:
            # capture exceptions which are related to strings only
            if re.match(r"^[\d]+$", v):
                value = int(v)
            elif re.match(r"^True$", v):
                value = True
            elif re.match(r"^False$", v):
                value = False
            elif re.match(r"^None$", v):
                value = None
            elif re.match(r"^[\w\d_]+$", v):
                value = v
            else:
                value = ast.literal_eval(v)
        except (ValueError, SyntaxError) as msg:
            log.warning(msg)
            value = v

        data[key] = value

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
    project_name = legacy_io.Session["AVALON_PROJECT"]

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
        # old way of setting it
        project.setProjectRoot(active_project_root)

    # get project data from avalon db
    project_doc = legacy_io.find_one({"type": "project"})
    project_data = project_doc["data"]

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
        publish(hiero.ui.mainWindow())


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
        publish(hiero.ui.mainWindow())

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
#     from openpype.hosts.nuke.api.lib import (
#         BuildWorkfile,
#         imprint
#     )
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
#     script_builder = BuildWorkfile(
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
    # todo will need to define this better
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

    # make sure only trackItems are in list selection
    only_track_items = [
        i for i in track_items_list
        if isinstance(i, hiero.core.TrackItem)]

    # Getting selection
    timeline_editor = hiero.ui.getTimelineEditor(_sequence)
    return timeline_editor.setSelection(only_track_items)


def _read_doc_from_path(path):
    # reading QDomDocument from HROX path
    hrox_file = QFile(path)
    if not hrox_file.open(QFile.ReadOnly):
        raise RuntimeError("Failed to open file for reading")
    doc = QDomDocument()
    doc.setContent(hrox_file)
    hrox_file.close()
    return doc


def _write_doc_to_path(doc, path):
    # write QDomDocument to path as HROX
    hrox_file = QFile(path)
    if not hrox_file.open(QFile.WriteOnly):
        raise RuntimeError("Failed to open file for writing")
    stream = QTextStream(hrox_file)
    doc.save(stream, 1)
    hrox_file.close()


def _set_hrox_project_knobs(doc, **knobs):
    # set attributes to Project Tag
    proj_elem = doc.documentElement().firstChildElement("Project")
    for k, v in knobs.items():
        if "ocioconfigpath" in k:
            paths_to_format = v[platform.system().lower()]
            for _path in paths_to_format:
                v = _path.format(**os.environ)
                if not os.path.exists(v):
                    continue
        log.debug("Project colorspace knob `{}` was set to `{}`".format(k, v))
        if isinstance(v, dict):
            continue
        proj_elem.setAttribute(str(k), v)


def apply_colorspace_project():
    project_name = os.getenv("AVALON_PROJECT")
    # get path the the active projects
    project = get_current_project(remove_untitled=True)
    current_file = project.path()

    # close the active project
    project.close()

    # get presets for hiero
    imageio = get_anatomy_settings(
        project_name)["imageio"].get("hiero", None)
    presets = imageio.get("workfile")

    # save the workfile as subversion "comment:_colorspaceChange"
    split_current_file = os.path.splitext(current_file)
    copy_current_file = current_file

    if "_colorspaceChange" not in current_file:
        copy_current_file = (
            split_current_file[0]
            + "_colorspaceChange"
            + split_current_file[1]
        )

    try:
        # duplicate the file so the changes are applied only to the copy
        shutil.copyfile(current_file, copy_current_file)
    except shutil.Error:
        # in case the file already exists and it want to copy to the
        # same filewe need to do this trick
        # TEMP file name change
        copy_current_file_tmp = copy_current_file + "_tmp"
        # create TEMP file
        shutil.copyfile(current_file, copy_current_file_tmp)
        # remove original file
        os.remove(current_file)
        # copy TEMP back to original name
        shutil.copyfile(copy_current_file_tmp, copy_current_file)
        # remove the TEMP file as we dont need it
        os.remove(copy_current_file_tmp)

    # use the code from below for changing xml hrox Attributes
    presets.update({"name": os.path.basename(copy_current_file)})

    # read HROX in as QDomSocument
    doc = _read_doc_from_path(copy_current_file)

    # apply project colorspace properties
    _set_hrox_project_knobs(doc, **presets)

    # write QDomSocument back as HROX
    _write_doc_to_path(doc, copy_current_file)

    # open the file as current project
    hiero.core.openProject(copy_current_file)


def apply_colorspace_clips():
    project_name = os.getenv("AVALON_PROJECT")
    project = get_current_project(remove_untitled=True)
    clips = project.clips()

    # get presets for hiero
    imageio = get_anatomy_settings(
        project_name)["imageio"].get("hiero", None)
    from pprint import pprint

    presets = imageio.get("regexInputs", {}).get("inputs", {})
    pprint(presets)
    for clip in clips:
        clip_media_source_path = clip.mediaSource().firstpath()
        clip_name = clip.name()
        clip_colorspace = clip.sourceMediaColourTransform()

        if "default" in clip_colorspace:
            continue

        # check if any colorspace presets for read is matching
        preset_clrsp = None
        for k in presets:
            if not bool(re.search(k["regex"], clip_media_source_path)):
                continue
            preset_clrsp = k["colorspace"]

        if preset_clrsp:
            log.debug("Changing clip.path: {}".format(clip_media_source_path))
            log.info("Changing clip `{}` colorspace {} to {}".format(
                clip_name, clip_colorspace, preset_clrsp))
            # set the found preset to the clip
            clip.setSourceMediaColourTransform(preset_clrsp)

    # save project after all is changed
    project.save()


def is_overlapping(ti_test, ti_original, strict=False):
    covering_exp = (
        (ti_test.timelineIn() <= ti_original.timelineIn())
        and (ti_test.timelineOut() >= ti_original.timelineOut())
    )
    inside_exp = (
        (ti_test.timelineIn() >= ti_original.timelineIn())
        and (ti_test.timelineOut() <= ti_original.timelineOut())
    )
    overlaying_right_exp = (
        (ti_test.timelineIn() < ti_original.timelineOut())
        and (ti_test.timelineOut() >= ti_original.timelineOut())
    )
    overlaying_left_exp = (
        (ti_test.timelineOut() > ti_original.timelineIn())
        and (ti_test.timelineIn() <= ti_original.timelineIn())
    )

    if strict:
        return covering_exp
    else:
        return any((
            covering_exp,
            inside_exp,
            overlaying_right_exp,
            overlaying_left_exp
        ))


def get_sequence_pattern_and_padding(file):
    """ Return sequence pattern and padding from file

    Attributes:
        file (string): basename form path

    Example:
        Can find file.0001.ext, file.%02d.ext, file.####.ext

    Return:
        string: any matching sequence pattern
        int: padding of sequnce numbering
    """
    foundall = re.findall(
        r"(#+)|(%\d+d)|(?<=[^a-zA-Z0-9])(\d+)(?=\.\w+$)", file)
    if not foundall:
        return None, None
    found = sorted(list(set(foundall[0])))[-1]

    padding = int(
        re.findall(r"\d+", found)[-1]) if "%" in found else len(found)
    return found, padding


def sync_clip_name_to_data_asset(track_items_list):
    # loop through all selected clips
    for track_item in track_items_list:
        # ignore if parent track is locked or disabled
        if track_item.parent().isLocked():
            continue
        if not track_item.parent().isEnabled():
            continue
        # ignore if the track item is disabled
        if not track_item.isEnabled():
            continue

        # get name and data
        ti_name = track_item.name()
        data = get_track_item_pype_data(track_item)

        # ignore if no data on the clip or not publish instance
        if not data:
            continue
        if data.get("id") != "pyblish.avalon.instance":
            continue

        # fix data if wrong name
        if data["asset"] != ti_name:
            data["asset"] = ti_name
            # remove the original tag
            tag = get_track_item_pype_tag(track_item)
            track_item.removeTag(tag)
            # create new tag with updated data
            set_track_item_pype_tag(track_item, data)
            print("asset was changed in clip: {}".format(ti_name))


def check_inventory_versions(track_items=None):
    """
    Actual version color idetifier of Loaded containers

    Check all track items and filter only
    Loader nodes for its version. It will get all versions from database
    and check if the node is having actual version. If not then it will color
    it to red.
    """
    from . import parse_container

    track_item = track_items or get_track_items()
    # presets
    clip_color_last = "green"
    clip_color = "red"

    # get all track items from current timeline
    for track_item in track_item:
        container = parse_container(track_item)
        if container:
            # get representation from io
            representation = legacy_io.find_one({
                "type": "representation",
                "_id": ObjectId(container["representation"])
            })

            # Get start frame from version data
            version = legacy_io.find_one({
                "type": "version",
                "_id": representation["parent"]
            })

            # get all versions in list
            versions = legacy_io.find({
                "type": "version",
                "parent": version["parent"]
            }).distinct('name')

            max_version = max(versions)

            # set clip colour
            if version.get("name") == max_version:
                track_item.source().binItem().setColor(clip_color_last)
            else:
                track_item.source().binItem().setColor(clip_color)


def selection_changed_timeline(event):
    """Callback on timeline to check if asset in data is the same as clip name.

    Args:
        event (hiero.core.Event): timeline event
    """
    timeline_editor = event.sender
    selection = timeline_editor.selection()

    track_items = get_track_items(
        selection=selection,
        track_type="video",
        check_enabled=True,
        check_locked=True,
        check_tagged=True
    )

    # run checking function
    sync_clip_name_to_data_asset(track_items)


def before_project_save(event):
    track_items = get_track_items(
        track_type="video",
        check_enabled=True,
        check_locked=True,
        check_tagged=True
    )

    # run checking function
    sync_clip_name_to_data_asset(track_items)

    # also mark old versions of loaded containers
    check_inventory_versions(track_items)


def get_main_window():
    """Acquire Nuke's main window"""
    if self._parent is None:
        top_widgets = QtWidgets.QApplication.topLevelWidgets()
        name = "Foundry::UI::DockMainWindow"
        main_window = next(widget for widget in top_widgets if
                           widget.inherits("QMainWindow") and
                           widget.metaObject().className() == name)
        self._parent = main_window
    return self._parent
