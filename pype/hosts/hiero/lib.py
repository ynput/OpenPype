"""
Host specific functions where host api is connected
"""
import os
import re
import sys
import ast
import hiero
import avalon.api as avalon
# from opentimelineio import opentime
from avalon.vendor.Qt import QtWidgets
import pype.api as pype
from pype.api import Logger, Anatomy
from . import tags
from pprint import pformat

log = Logger().get_logger(__name__, "hiero")

self = sys.modules[__name__]
self._has_been_setup = False
self._has_menu = False
self._registered_gui = None
self.pype_tag_name = "Pype Data"
self.vertical_clip_match = {}

AVALON_CONFIG = os.getenv("AVALON_CONFIG", "pype")


def get_current_project():
    return next(iter(hiero.core.projects()))


def get_current_sequence():
    return hiero.ui.activeSequence()


def get_track_items(
        selected=False,
        track_name=None,
        track_type=None,
        check_enabled=False):
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
            # and all items in track
            for item in track.items():
                # check if track item is enabled
                if check_enabled:
                    if not item.isEnabled():
                        continue
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
    data = data or {}

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
        log.debug((k, v))
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


class ClipLoader:

    active_bin = None

    def __init__(self, plugin_cls, context, sequence=None,
                 track=None, **kwargs):
        """ Initialize object

        Arguments:
            plugin_cls (api.Loader): plugin object
            context (dict): loader plugin context
            sequnce (hiero.core.Sequence): sequence object
            track (hiero.core.Track): track object
            kwargs (dict)[optional]: possible keys:
                projectBinPath: "path/to/binItem"
                hieroWorkfileName: "name_of_hiero_project_file_no_extension"

        """
        self.cls = plugin_cls
        self.context = context
        self.kwargs = kwargs
        self.active_project = self._get_active_project()
        self.project_bin = self.active_project.clipsBin()

        self.data = dict()

        assert self._set_data(), str(
            "Cannot Load selected data, look into database "
            "or call your supervisor")

        # inject asset data to representation dict
        self._get_asset_data()
        log.debug("__init__ self.data: `{}`".format(self.data))

        # add active components to class
        self.active_sequence = self._get_active_sequence(sequence)
        self.active_track = self._get_active_track(track)

    def _set_data(self):
        """ Gets context and convert it to self.data
        data structure:
            {
                "name": "assetName_subsetName_representationName"
                "path": "path/to/file/created/by/get_repr..",
                "binPath": "projectBinPath",
            }
        """
        # create name
        repr = self.context["representation"]
        repr_cntx = repr["context"]
        asset = str(repr_cntx["asset"])
        subset = str(repr_cntx["subset"])
        representation = str(repr_cntx["representation"])
        self.data["clip_name"] = "_".join([asset, subset, representation])
        self.data["track_name"] = "_".join([subset, representation])

        # gets file path
        file = self.cls.fname
        if not file:
            repr_id = repr["_id"]
            log.warning(
                "Representation id `{}` is failing to load".format(repr_id))
            return None
        self.data["path"] = file.replace("\\", "/")

        # convert to hashed path
        if repr_cntx.get("frame"):
            self._fix_path_hashes()

        # solve project bin structure path
        hierarchy = str("/".join((
            "Loader",
            repr_cntx["hierarchy"].replace("\\", "/"),
            asset
        )))

        self.data["binPath"] = self.kwargs.get(
            "projectBinPath",
            hierarchy
        )

        return True

    def _fix_path_hashes(self):
        """ Convert file path where it is needed padding with hashes
        """
        file = self.data["path"]
        if "#" not in file:
            frame = self.context["representation"]["context"].get("frame")
            padding = len(frame)
            file = file.replace(frame, "#" * padding)
        self.data["path"] = file

    def _get_active_project(self):
        """ Get hiero active project object
        """
        fname = self.kwargs.get("hieroWorkfileName", "")

        return next((p for p in hiero.core.projects()
                     if fname in p.name()),
                    hiero.core.projects()[-1])

    def _get_asset_data(self):
        """ Get all available asset data

        joint `data` key with asset.data dict into the representaion

        """
        asset_name = self.context["representation"]["context"]["asset"]
        self.data["assetData"] = pype.get_asset(asset_name)["data"]

    def _make_project_bin(self, hierarchy):
        """ Creare bins by given hierarchy path

        It will also make sure no duplicit bins will be created

        Arguments:
            hierarchy (str): path devided by slashes "bin0/bin1/bin2"

        Returns:
            bin (hiero.core.BinItem): with the bin to be used for mediaItem
        """
        if self.active_bin:
            return self.active_bin

        assert hierarchy != "", "Please add hierarchy!"
        log.debug("__ hierarchy1: `{}`".format(hierarchy))
        if '/' in hierarchy:
            hierarchy = hierarchy.split('/')
        else:
            hierarchy = [hierarchy]

        parent_bin = None
        for i, name in enumerate(hierarchy):
            # if first index and list is more then one long
            if i == 0:
                bin = next((bin for bin in self.project_bin.bins()
                            if name in bin.name()), None)
                if not bin:
                    bin = hiero.core.Bin(name)
                    self.project_bin.addItem(bin)
                log.debug("__ bin.name: `{}`".format(bin.name()))
                parent_bin = bin

            # if second to prelast
            elif (i >= 1) and (i <= (len(hierarchy) - 1)):
                bin = next((bin for bin in parent_bin.bins()
                            if name in bin.name()), None)
                if not bin:
                    bin = hiero.core.Bin(name)
                    parent_bin.addItem(bin)

                parent_bin = bin

        return parent_bin

    def _make_track_item(self):
        """ Create track item with """
        pass

    def _set_clip_color(self, last_version=True):
        """ Sets color of clip on clip/track item

        Arguments:
            last_version (bool): True = green | False = red
        """
        pass

    def _set_container_tag(self, item, metadata):
        """ Sets container tag to given clip/track item

        Arguments:
            item (hiero.core.BinItem or hiero.core.TrackItem)
            metadata (dict): data to be added to tag
        """
        pass

    def _get_active_sequence(self, sequence):
        if not sequence:
            return get_current_sequence()
        else:
            return sequence

    def _get_active_track(self, track):
        if not track:
            track_name = self.data["track_name"]
        else:
            track_name = track.name()

        track_pass = next(
            (t for t in self.active_sequence.videoTracks()
             if t.name() in track_name), None
        )

        if not track_pass:
            track_pass = hiero.core.VideoTrack(track_name)
            self.active_sequence.addTrack(track_pass)

        return track_pass

    def load(self):
        log.debug("__ active_project: `{}`".format(self.active_project))
        log.debug("__ active_sequence: `{}`".format(self.active_sequence))

        # create project bin for the media to be imported into
        self.active_bin = self._make_project_bin(self.data["binPath"])
        log.debug("__ active_bin: `{}`".format(self.active_bin))

        log.debug("__ version.data: `{}`".format(
            self.context["version"]["data"]))

        # create mediaItem in active project bin
        # create clip media
        media = hiero.core.MediaSource(self.data["path"])
        media_duration = int(media.duration())

        handle_start = int(self.data["assetData"]["handleStart"])
        handle_end = int(self.data["assetData"]["handleEnd"])

        clip_in = int(self.data["assetData"]["clipIn"])
        clip_out = int(self.data["assetData"]["clipOut"])

        log.debug("__ media_duration: `{}`".format(media_duration))
        log.debug("__ handle_start: `{}`".format(handle_start))
        log.debug("__ handle_end: `{}`".format(handle_end))
        log.debug("__ clip_in: `{}`".format(clip_in))
        log.debug("__ clip_out: `{}`".format(clip_out))

        # check if slate is included
        # either in version data families or by calculating frame diff
        slate_on = next(
            (f for f in self.context["version"]["data"]["families"]
             if "slate" in f),
            # if nothing was found then use default None
            # so other bool could be used
            None) or bool(((
                clip_out - clip_in + 1) + handle_start + handle_end
            ) - media_duration)

        log.debug("__ slate_on: `{}`".format(slate_on))

        # calculate slate differences
        if slate_on:
            media_duration -= 1
            handle_start += 1

        # create Clip from Media
        _clip = hiero.core.Clip(media)
        _clip.setName(self.data["clip_name"])

        # add Clip to bin if not there yet
        if self.data["clip_name"] not in [
                b.name()
                for b in self.active_bin.items()]:
            binItem = hiero.core.BinItem(_clip)
            self.active_bin.addItem(binItem)

        _source = next((item for item in self.active_bin.items()
                        if self.data["clip_name"] in item.name()), None)

        if not _source:
            log.warning("Problem with created Source clip: `{}`".format(
                self.data["clip_name"]))

        version = next((s for s in _source.items()), None)
        clip = version.item()

        # add to track as clip item
        track_item = hiero.core.TrackItem(
            self.data["clip_name"], hiero.core.TrackItem.kVideo)

        track_item.setSource(clip)

        track_item.setSourceIn(handle_start)
        track_item.setTimelineIn(clip_in)

        track_item.setSourceOut(media_duration - handle_end)
        track_item.setTimelineOut(clip_out)
        track_item.setPlaybackSpeed(1)
        self.active_track.addTrackItem(track_item)

        log.info("Loading clips: `{}`".format(self.data["clip_name"]))


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
        bin = create_bin_in_project(task_path, proj)

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


def create_bin_in_project(bin_name='', project=''):
    '''
    create bin in project and
    if the bin_name is "bin1/bin2/bin3" it will create whole depth
    '''

    if not project:
        # get the first loaded project
        project = hiero.core.projects()[-1]
    if not bin_name:
        return None
    if '/' in bin_name:
        bin_name = bin_name.split('/')
    else:
        bin_name = [bin_name]

    clipsBin = project.clipsBin()

    done_bin_lst = []
    for i, b in enumerate(bin_name):
        if i == 0 and len(bin_name) > 1:
            if b in [bin.name() for bin in clipsBin.bins()]:
                bin = [bin for bin in clipsBin.bins() if b in bin.name()][0]
                done_bin_lst.append(bin)
            else:
                create_bin = hiero.core.Bin(b)
                clipsBin.addItem(create_bin)
                done_bin_lst.append(create_bin)

        elif i >= 1 and i < len(bin_name) - 1:
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

        elif i == len(bin_name) - 1:
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
    # print [bin.name() for bin in clipsBin.bins()]
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


def create_publish_clip(cls, track_item, rename=False, **kwargs):
    """
    Convert a track item to publishable instance

    Args:
        track_item (hiero.core.TrackItem): hiero track item object
        rename (bool)[optional]: renaming in sequence or not
        kwargs (optional): additional data needed for rename=True (presets)

    Returns:
        hiero.core.TrackItem: hiero track item object with pype tag
    """
    tag_data = dict()

    # get main parent objects
    sequence = get_current_sequence()

    # track item (clip) main attributes
    ti_name = track_item.name()
    ti_index = track_item.eventNumber()

    # get track name and index
    track_name = track_item.parent().name()
    track_index = track_item.parent().trackIndex()

    # collect track item data for farther processing
    track_item_data = {
        "_folder_": "shots",
        "_sequence_": str(sequence.name()).replace(" ", "_"),
        "_track_": str(track_name).replace(" ", "_"),
        "_clip_": ti_name,
        "_trackIndex_": int(track_index),
        "_clipIndex_": int(ti_index)
    }

    # adding tag.family into tag
    if kwargs.get("avalon"):
        tag_data.update(kwargs["avalon"])

    # log.debug("_ tag_data1: {}".format(pformat(tag_data)))

    # solve track item data and add them to tag data
    track_item_data_tag = create_track_item_data(
        cls, track_item, track_item_data, kwargs.get("ui_inputs")
    )
    tag_data.update(track_item_data_tag)

    # deal with clip name
    new_name = tag_data.pop("newClipName")
    # log.debug("_ new_name: {}".format(new_name))
    if rename:
        # rename track item
        track_item.setName(new_name)
        tag_data["asset"] = new_name
    else:
        tag_data["asset"] = ti_name

    # log.debug("_ tag_data1: {}".format(pformat(tag_data)))

    # create pype tag on track_item and add data
    imprint(track_item, tag_data)

    return track_item


def create_track_item_data(cls, track_item, track_item_data, ui_inputs=None):
    """
    Take hierarchy data from presets and build name with parents data

    Args:
        cls (pype.hosts.hiero.Creator): instance of creator class
        track_item_data (dict): additional track item objects
        ui_inputs (dict): data from create plugin

    Returns:
        list: name, data

    """
    def _replace_hash_to_expression(name, text):
        _spl = text.split("#")
        _len = (len(_spl) - 1)
        _repl = "{{{0}:0>{1}}}".format(name, _len)
        new_text = text.replace(("#" * _len), _repl)
        return new_text

    # track item frame range and parent track name for vertical sync check
    clip_in = int(track_item.timelineIn())
    clip_out = int(track_item.timelineOut())
    track_name = track_item.parent().name()
    track_index = track_item.parent().trackIndex()

    # define ui inputs if non gui mode was used
    ui_inputs = ui_inputs or {}
    shot_num = track_item.eventNumber()

    # define return data
    return_data = dict()

    # ui_inputs data or default values if gui was not used
    clip_name = ui_inputs.get("clipName", {}).get("value") \
        or "shot_{_trackIndex_:0>3}_{_clipIndex_:0>4}"
    hierarchy = ui_inputs.get("hierarchy", {}).get("value") \
        or "{_folder_}/{_sequence_}/{_track_}"
    hierarchy_data = ui_inputs.get("hierarchyData", {}).get("value") \
        or track_item_data.copy()
    count_from = ui_inputs.get("countFrom", {}).get("value") or 10
    count_steps = ui_inputs.get("countSteps", {}).get("value") or 10
    subset_name = ui_inputs.get(
        "subsetName", {}).get("value") or "<track_name>"
    subset_family = ui_inputs.get(
        "subsetFamily", {}).get("value") or "plate"

    # build subset name from layer name
    if subset_name == "<track_name>":
        subset_name = track_item_data["_track_"]

    # create subset for publishing
    subset = subset_family + subset_name.capitalize()

    # vertical sync attributes
    vertical_sync = ui_inputs.get("vSyncOn", {}).get("value") or None
    driving_layer = ui_inputs.get("vSyncTrack", {}).get("value") or ""

    # define vertical sync attributes
    master_layer = True
    if vertical_sync:
        # check if track name is not in driving layer
        if track_name not in driving_layer:
            # if it is not then define vertical sync as None
            master_layer = False

    # driving layer is set as positive match
    hierarchy_data_tag = dict()
    _data = track_item_data.copy()
    if ui_inputs:
        # adding tag metadata from ui
        for _k, _v in ui_inputs.items():
            if _v["target"] == "tag":
                return_data[_k] = _v["value"]

        if master_layer and vertical_sync:
            # reset rename_add
            if cls.rename_add < count_from:
                cls.rename_add = count_from

            # shot num calculate
            if cls.rename_index == 0:
                shot_num = cls.rename_add
            else:
                shot_num = cls.rename_add + count_steps

        # clip name sequence number
        _data.update({"shot": shot_num})
        cls.rename_add = shot_num

        # solve # in test to pythonic expression
        for _k, _v in hierarchy_data.items():
            if "#" not in _v["value"]:
                continue
            hierarchy_data[_k]["value"] = _replace_hash_to_expression(
                _k, _v["value"])

        # fill up pythonic expresisons in hierarchy data
        for k, _v in hierarchy_data.items():
            hierarchy_data_tag[k] = _v["value"].format(**_data)
    else:
        # if no gui mode then just pass default data
        hierarchy_data_tag = hierarchy_data

    # fill up clip name and hierarchy keys
    hierarchy = hierarchy.format(**hierarchy_data_tag)
    clip_name = clip_name.format(**hierarchy_data_tag)

    return_data_hierarchy = {
        "newClipName": clip_name,
        "hierarchy": hierarchy,
        "hierarchyData": hierarchy_data_tag,
        "subset": subset
    }

    if master_layer and vertical_sync:
        self.vertical_clip_match.update({
            (clip_in, clip_out): return_data_hierarchy
        })

    if not master_layer and vertical_sync:
        # driving layer is set as negative match
        for (_in, _out), data in self.vertical_clip_match.items():
            if _in == clip_in and _out == clip_out:
                data_subset = data["subset"]
                # add track index in case duplicity of names in master data
                if subset in data_subset:
                    subset = subset + str(track_index)
                    data["subset"] = subset
                # in case track name and subset name is the same then add
                if subset_name == str(track_name).replace(" ", "_"):
                    data["subset"] = subset
                # assing data to return hierarchy data to tag
                return_data_hierarchy = data

    # add data to return data dict
    return_data.update(return_data_hierarchy)

    return return_data
