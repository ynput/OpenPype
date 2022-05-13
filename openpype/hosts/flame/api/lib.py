import sys
import os
import re
import json
import pickle
import clique
import tempfile
import itertools
import contextlib
import xml.etree.cElementTree as cET
from copy import deepcopy
from xml.etree import ElementTree as ET
from pprint import pformat
from .constants import (
    MARKER_COLOR,
    MARKER_DURATION,
    MARKER_NAME,
    COLOR_MAP,
    MARKER_PUBLISH_DEFAULT
)

import openpype.api as openpype

log = openpype.Logger.get_logger(__name__)

FRAME_PATTERN = re.compile(r"[\._](\d+)[\.]")


class CTX:
    # singleton used for passing data between api modules
    app_framework = None
    flame_apps = []
    selection = None


@contextlib.contextmanager
def io_preferences_file(klass, filepath, write=False):
    try:
        flag = "w" if write else "r"
        yield open(filepath, flag)

    except IOError as _error:
        klass.log.info("Unable to work with preferences `{}`: {}".format(
            filepath, _error))


class FlameAppFramework(object):
    # flameAppFramework class takes care of preferences

    class prefs_dict(dict):

        def __init__(self, master, name, **kwargs):
            self.name = name
            self.master = master
            if not self.master.get(self.name):
                self.master[self.name] = {}
            self.master[self.name].__init__()

        def __getitem__(self, k):
            return self.master[self.name].__getitem__(k)

        def __setitem__(self, k, v):
            return self.master[self.name].__setitem__(k, v)

        def __delitem__(self, k):
            return self.master[self.name].__delitem__(k)

        def get(self, k, default=None):
            return self.master[self.name].get(k, default)

        def setdefault(self, k, default=None):
            return self.master[self.name].setdefault(k, default)

        def pop(self, *args, **kwargs):
            return self.master[self.name].pop(*args, **kwargs)

        def update(self, mapping=(), **kwargs):
            self.master[self.name].update(mapping, **kwargs)

        def __contains__(self, k):
            return self.master[self.name].__contains__(k)

        def copy(self):  # don"t delegate w/ super - dict.copy() -> dict :(
            return type(self)(self)

        def keys(self):
            return self.master[self.name].keys()

        @classmethod
        def fromkeys(cls, keys, v=None):
            return cls.master[cls.name].fromkeys(keys, v)

        def __repr__(self):
            return "{0}({1})".format(
                type(self).__name__, self.master[self.name].__repr__())

        def master_keys(self):
            return self.master.keys()

    def __init__(self):
        self.name = self.__class__.__name__
        self.bundle_name = "OpenPypeFlame"
        # self.prefs scope is limited to flame project and user
        self.prefs = {}
        self.prefs_user = {}
        self.prefs_global = {}
        self.log = log

        try:
            import flame
            self.flame = flame
            self.flame_project_name = self.flame.project.current_project.name
            self.flame_user_name = flame.users.current_user.name
        except Exception:
            self.flame = None
            self.flame_project_name = None
            self.flame_user_name = None

        import socket
        self.hostname = socket.gethostname()

        if sys.platform == "darwin":
            self.prefs_folder = os.path.join(
                os.path.expanduser("~"),
                "Library",
                "Caches",
                "OpenPype",
                self.bundle_name
            )
        elif sys.platform.startswith("linux"):
            self.prefs_folder = os.path.join(
                os.path.expanduser("~"),
                ".OpenPype",
                self.bundle_name)

        self.prefs_folder = os.path.join(
            self.prefs_folder,
            self.hostname,
        )

        self.log.info("[{}] waking up".format(self.__class__.__name__))

        try:
            self.load_prefs()
        except RuntimeError:
            self.save_prefs()

        # menu auto-refresh defaults
        if not self.prefs_global.get("menu_auto_refresh"):
            self.prefs_global["menu_auto_refresh"] = {
                "media_panel": True,
                "batch": True,
                "main_menu": True,
                "timeline_menu": True
            }

        self.apps = []

    def get_pref_file_paths(self):

        prefix = self.prefs_folder + os.path.sep + self.bundle_name
        prefs_file_path = "_".join([
            prefix, self.flame_user_name,
            self.flame_project_name]) + ".prefs"
        prefs_user_file_path = "_".join([
            prefix, self.flame_user_name]) + ".prefs"
        prefs_global_file_path = prefix + ".prefs"

        return (prefs_file_path, prefs_user_file_path, prefs_global_file_path)

    def load_prefs(self):

        (proj_pref_path, user_pref_path,
         glob_pref_path) = self.get_pref_file_paths()

        with io_preferences_file(self, proj_pref_path) as prefs_file:
            self.prefs = pickle.load(prefs_file)
            self.log.info(
                "Project - preferences contents:\n{}".format(
                    pformat(self.prefs)
                ))

        with io_preferences_file(self, user_pref_path) as prefs_file:
            self.prefs_user = pickle.load(prefs_file)
            self.log.info(
                "User - preferences contents:\n{}".format(
                    pformat(self.prefs_user)
                ))

        with io_preferences_file(self, glob_pref_path) as prefs_file:
            self.prefs_global = pickle.load(prefs_file)
            self.log.info(
                "Global - preferences contents:\n{}".format(
                    pformat(self.prefs_global)
                ))

        return True

    def save_prefs(self):
        # make sure the preference folder is available
        if not os.path.isdir(self.prefs_folder):
            try:
                os.makedirs(self.prefs_folder)
            except Exception:
                self.log.info("Unable to create folder {}".format(
                    self.prefs_folder))
                return False

        # get all pref file paths
        (proj_pref_path, user_pref_path,
         glob_pref_path) = self.get_pref_file_paths()

        with io_preferences_file(self, proj_pref_path, True) as prefs_file:
            pickle.dump(self.prefs, prefs_file)
            self.log.info(
                "Project - preferences contents:\n{}".format(
                    pformat(self.prefs)
                ))

        with io_preferences_file(self, user_pref_path, True) as prefs_file:
            pickle.dump(self.prefs_user, prefs_file)
            self.log.info(
                "User - preferences contents:\n{}".format(
                    pformat(self.prefs_user)
                ))

        with io_preferences_file(self, glob_pref_path, True) as prefs_file:
            pickle.dump(self.prefs_global, prefs_file)
            self.log.info(
                "Global - preferences contents:\n{}".format(
                    pformat(self.prefs_global)
                ))

        return True


def get_current_project():
    import flame
    return flame.project.current_project


def get_current_sequence(selection):
    import flame

    def segment_to_sequence(_segment):
        track = _segment.parent
        version = track.parent
        return version.parent

    process_timeline = None

    if len(selection) == 1:
        if isinstance(selection[0], flame.PySequence):
            process_timeline = selection[0]
        if isinstance(selection[0], flame.PySegment):
            process_timeline = segment_to_sequence(selection[0])
    else:
        for segment in selection:
            if isinstance(segment, flame.PySegment):
                process_timeline = segment_to_sequence(segment)
                break

    return process_timeline


def rescan_hooks():
    import flame
    try:
        flame.execute_shortcut('Rescan Python Hooks')
    except Exception:
        pass


def get_metadata(project_name, _log=None):
    # TODO: can be replaced by MediaInfoFile class method
    from adsk.libwiretapPythonClientAPI import (
        WireTapClient,
        WireTapServerHandle,
        WireTapNodeHandle,
        WireTapStr
    )

    class GetProjectColorPolicy(object):
        def __init__(self, host_name=None, _log=None):
            # Create a connection to the Backburner manager using the Wiretap
            # python API.
            #
            self.log = _log or log
            self.host_name = host_name or "localhost"
            self._wiretap_client = WireTapClient()
            if not self._wiretap_client.init():
                raise Exception("Could not initialize Wiretap Client")
            self._server = WireTapServerHandle(
                "{}:IFFFS".format(self.host_name))

        def process(self, project_name):
            policy_node_handle = WireTapNodeHandle(
                self._server,
                "/projects/{}/syncolor/policy".format(project_name)
            )
            self.log.info(policy_node_handle)

            policy = WireTapStr()
            if not policy_node_handle.getNodeTypeStr(policy):
                self.log.warning(
                    "Could not retrieve policy of '%s': %s" % (
                        policy_node_handle.getNodeId().id(),
                        policy_node_handle.lastError()
                    )
                )

            return policy.c_str()

    policy_wiretap = GetProjectColorPolicy(_log=_log)
    return policy_wiretap.process(project_name)


def get_segment_data_marker(segment, with_marker=None):
    """
    Get openpype track item tag created by creator or loader plugin.

    Attributes:
        segment (flame.PySegment): flame api object
        with_marker (bool)[optional]: if true it will return also marker object

    Returns:
        dict: openpype tag data

    Returns(with_marker=True):
        flame.PyMarker, dict
    """
    for marker in segment.markers:
        comment = marker.comment.get_value()
        color = marker.colour.get_value()
        name = marker.name.get_value()

        if (name == MARKER_NAME) and (
                color == COLOR_MAP[MARKER_COLOR]):
            if not with_marker:
                return json.loads(comment)
            else:
                return marker, json.loads(comment)


def set_segment_data_marker(segment, data=None):
    """
    Set openpype track item tag to input segment.

    Attributes:
        segment (flame.PySegment): flame api object

    Returns:
        dict: json loaded data
    """
    data = data or dict()

    marker_data = get_segment_data_marker(segment, True)

    if marker_data:
        # get available openpype tag if any
        marker, tag_data = marker_data
        # update tag data with new data
        tag_data.update(data)
        # update marker with tag data
        marker.comment = json.dumps(tag_data)
    else:
        # update tag data with new data
        marker = create_segment_data_marker(segment)
        # add tag data to marker's comment
        marker.comment = json.dumps(data)


def set_publish_attribute(segment, value):
    """ Set Publish attribute in input Tag object

    Attribute:
        segment (flame.PySegment)): flame api object
        value (bool): True or False
    """
    tag_data = get_segment_data_marker(segment)
    tag_data["publish"] = value

    # set data to the publish attribute
    set_segment_data_marker(segment, tag_data)


def get_publish_attribute(segment):
    """ Get Publish attribute from input Tag object

    Attribute:
        segment (flame.PySegment)): flame api object

    Returns:
        bool: True or False
    """
    tag_data = get_segment_data_marker(segment)

    if not tag_data:
        set_publish_attribute(segment, MARKER_PUBLISH_DEFAULT)
        return MARKER_PUBLISH_DEFAULT

    return tag_data["publish"]


def create_segment_data_marker(segment):
    """ Create openpype marker on a segment.

    Attributes:
        segment (flame.PySegment): flame api object

    Returns:
        flame.PyMarker: flame api object
    """
    # get duration of segment
    duration = segment.record_duration.relative_frame
    # calculate start frame of the new marker
    start_frame = int(segment.record_in.relative_frame) + int(duration / 2)
    # create marker
    marker = segment.create_marker(start_frame)
    # set marker name
    marker.name = MARKER_NAME
    # set duration
    marker.duration = MARKER_DURATION
    # set colour
    marker.colour = COLOR_MAP[MARKER_COLOR]  # Red

    return marker


def get_sequence_segments(sequence, selected=False):
    segments = []
    # loop versions in sequence
    for ver in sequence.versions:
        # loop track in versions
        for track in ver.tracks:
            # ignore all empty tracks and hidden too
            if len(track.segments) == 0 and track.hidden:
                continue
            # loop all segment in remaining tracks
            for segment in track.segments:
                if segment.name.get_value() == "":
                    continue
                if segment.hidden.get_value() is True:
                    continue
                if (
                    selected is True
                    and segment.selected.get_value() is not True
                ):
                    continue
                # add it to original selection
                segments.append(segment)
    return segments


@contextlib.contextmanager
def maintained_segment_selection(sequence):
    """Maintain selection during context

    Attributes:
        sequence (flame.PySequence): python api object

    Yield:
        list of flame.PySegment

    Example:
        >>> with maintained_segment_selection(sequence) as selected_segments:
        ...     for segment in selected_segments:
        ...         segment.selected = False
        >>> print(segment.selected)
        True
    """
    selected_segments = get_sequence_segments(sequence, True)
    try:
        # do the operation on selected segments
        yield selected_segments
    finally:
        # reset all selected clips
        reset_segment_selection(sequence)
        # select only original selection of segments
        for segment in selected_segments:
            segment.selected = True


def reset_segment_selection(sequence):
    """Deselect all selected nodes
    """
    for ver in sequence.versions:
        for track in ver.tracks:
            if len(track.segments) == 0 and track.hidden:
                continue
            for segment in track.segments:
                segment.selected = False


def _get_shot_tokens_values(clip, tokens):
    old_value = None
    output = {}

    if not clip.shot_name:
        return output

    old_value = clip.shot_name.get_value()

    for token in tokens:
        clip.shot_name.set_value(token)
        _key = str(re.sub("[<>]", "", token)).replace(" ", "_")

        try:
            output[_key] = int(clip.shot_name.get_value())
        except ValueError:
            output[_key] = clip.shot_name.get_value()

    clip.shot_name.set_value(old_value)

    return output


def get_segment_attributes(segment):
    if segment.name.get_value() == "":
        return None

    # Add timeline segment to tree
    clip_data = {
        "shot_name": segment.shot_name.get_value(),
        "segment_name": segment.name.get_value(),
        "segment_comment": segment.comment.get_value(),
        "tape_name": segment.tape_name,
        "source_name": segment.source_name,
        "fpath": segment.file_path,
        "PySegment": segment
    }

    # head and tail with forward compatibility
    if segment.head:
        # `infinite` can be also returned
        if isinstance(segment.head, str):
            clip_data["segment_head"] = 0
        else:
            clip_data["segment_head"] = int(segment.head)
    if segment.tail:
        # `infinite` can be also returned
        if isinstance(segment.tail, str):
            clip_data["segment_tail"] = 0
        else:
            clip_data["segment_tail"] = int(segment.tail)

    # add all available shot tokens
    shot_tokens = _get_shot_tokens_values(segment, [
        "<colour space>", "<width>", "<height>", "<depth>", "<segment>",
        "<track>", "<track name>"
    ])
    clip_data.update(shot_tokens)

    # populate shot source metadata
    segment_attrs = [
        "record_duration", "record_in", "record_out",
        "source_duration", "source_in", "source_out"
    ]
    segment_attrs_data = {}
    for attr_name in segment_attrs:
        if not hasattr(segment, attr_name):
            continue
        attr = getattr(segment, attr_name)
        segment_attrs_data[attr_name] = str(attr).replace("+", ":")

        if attr_name in ["record_in", "record_out"]:
            clip_data[attr_name] = attr.relative_frame
        else:
            clip_data[attr_name] = attr.frame

    clip_data["segment_timecodes"] = segment_attrs_data

    return clip_data


def get_clips_in_reels(project):
    output_clips = []
    project_desktop = project.current_workspace.desktop

    for reel_group in project_desktop.reel_groups:
        for reel in reel_group.reels:
            for clip in reel.clips:
                clip_data = {
                    "PyClip": clip,
                    "fps": float(str(clip.frame_rate)[:-4])
                }

                attrs = [
                    "name", "width", "height",
                    "ratio", "sample_rate", "bit_depth"
                ]

                for attr in attrs:
                    val = getattr(clip, attr)
                    clip_data[attr] = val

                version = clip.versions[-1]
                track = version.tracks[-1]
                for segment in track.segments:
                    segment_data = get_segment_attributes(segment)
                    clip_data.update(segment_data)

                output_clips.append(clip_data)

    return output_clips


def get_reformated_filename(filename, padded=True):
    """
    Return fixed python expression path

    Args:
        filename (str): file name

    Returns:
        type: string with reformated path

    Example:
        get_reformated_filename("plate.1001.exr") > plate.%04d.exr

    """
    found = FRAME_PATTERN.search(filename)

    if not found:
        log.info("File name is not sequence: {}".format(filename))
        return filename

    padding = get_padding_from_filename(filename)

    replacement = "%0{}d".format(padding) if padded else "%d"
    start_idx, end_idx = found.span(1)

    return replacement.join(
        [filename[:start_idx], filename[end_idx:]]
    )


def get_padding_from_filename(filename):
    """
    Return padding number from Flame path style

    Args:
        filename (str): file name

    Returns:
        int: padding number

    Example:
        get_padding_from_filename("plate.0001.exr") > 4

    """
    found = get_frame_from_filename(filename)

    return len(found) if found else None


def get_frame_from_filename(filename):
    """
    Return sequence number from Flame path style

    Args:
        filename (str): file name

    Returns:
        int: sequence frame number

    Example:
        def get_frame_from_filename(path):
            ("plate.0001.exr") > 0001

    """

    found = re.findall(FRAME_PATTERN, filename)

    return found.pop() if found else None


@contextlib.contextmanager
def maintained_object_duplication(item):
    """Maintain input item duplication

    Attributes:
        item (any flame.PyObject): python api object

    Yield:
        duplicate input PyObject type
    """
    import flame
    # Duplicate the clip to avoid modifying the original clip
    duplicate = flame.duplicate(item)

    try:
        # do the operation on selected segments
        yield duplicate
    finally:
        # delete the item at the end
        flame.delete(duplicate)


@contextlib.contextmanager
def maintained_temp_file_path(suffix=None):
    _suffix = suffix or ""

    try:
        # Store dumped json to temporary file
        temporary_file = tempfile.mktemp(
            suffix=_suffix, prefix="flame_maintained_")
        yield temporary_file.replace("\\", "/")

    except IOError as _error:
        raise IOError(
            "Not able to create temp json file: {}".format(_error))

    finally:
        # Remove the temporary json
        os.remove(temporary_file)


def get_clip_segment(flame_clip):
    name = flame_clip.name.get_value()
    version = flame_clip.versions[0]
    track = version.tracks[0]
    segments = track.segments

    if len(segments) < 1:
        raise ValueError("Clip `{}` has no segments!".format(name))

    if len(segments) > 1:
        raise ValueError("Clip `{}` has too many segments!".format(name))

    return segments[0]


def get_batch_group_from_desktop(name):
    project = get_current_project()
    project_desktop = project.current_workspace.desktop

    for bgroup in project_desktop.batch_groups:
        if bgroup.name.get_value() in name:
            return bgroup


class MediaInfoFile(object):
    """Class to get media info file clip data

    Raises:
        IOError: MEDIA_SCRIPT_PATH path doesn't exists
        TypeError: Not able to generate clip xml data file
        ET.ParseError: Missing clip in xml clip data
        IOError: Not able to save xml clip data to file

    Attributes:
        str: `MEDIA_SCRIPT_PATH` path to flame binary
        logging.Logger: `log` logger

    TODO: add method for getting metadata to dict
    """
    MEDIA_SCRIPT_PATH = "/opt/Autodesk/mio/current/dl_get_media_info"

    log = log

    _clip_data = None
    _start_frame = None
    _fps = None
    _drop_mode = None
    _file_pattern = None

    def __init__(self, path, **kwargs):

        # replace log if any
        if kwargs.get("logger"):
            self.log = kwargs["logger"]

        # test if `dl_get_media_info` paht exists
        self._validate_media_script_path()

        # derivate other feed variables
        feed_basename = os.path.basename(path)
        feed_dir = os.path.dirname(path)
        feed_ext = os.path.splitext(feed_basename)[1][1:].lower()


        with maintained_temp_file_path(".clip") as tmp_path:
            self.log.info("Temp File: {}".format(tmp_path))
            self._generate_media_info_file(tmp_path, feed_ext, feed_dir)

            # get collection containing feed_basename from path
            self.file_pattern = self._get_collection(
                feed_basename, feed_dir, feed_ext)

            if (
                not self.file_pattern
                and os.path.exists(os.path.join(feed_dir, feed_basename))
            ):
                self.file_pattern = feed_basename

            # get clip data and make them single if there is multiple
            # clips data
            xml_data = self._make_single_clip_media_info(
                tmp_path, feed_basename, self.file_pattern)
            self.log.debug("xml_data: {}".format(xml_data))
            self.log.debug("type: {}".format(type(xml_data)))

            # get all time related data and assign them
            self._get_time_info_from_origin(xml_data)
            self.log.debug("start_frame: {}".format(self.start_frame))
            self.log.debug("fps: {}".format(self.fps))
            self.log.debug("drop frame: {}".format(self.drop_mode))
            self.clip_data = xml_data

    def _get_collection(self, feed_basename, feed_dir, feed_ext):
        """ Get collection string

        Args:
            feed_basename (str): file base name
            feed_dir (str): file's directory
            feed_ext (str): file extension

        Raises:
            AttributeError: feed_ext is not matching feed_basename

        Returns:
            str: collection basename with range of sequence
        """
        partialname = self._separate_file_head(feed_basename, feed_ext)
        self.log.debug("__ partialname: {}".format(partialname))

        # make sure partial input basename is having correct extensoon
        if not partialname:
            raise AttributeError("Wrong input attributes. Basename - {}, Ext - {}".format(
                feed_basename, feed_ext
            ))

        # get all related files
        files = [
            f for f in os.listdir(feed_dir)
            if partialname == self._separate_file_head(f, feed_ext)
        ]

        # ignore reminders as we dont need them
        collections = clique.assemble(files)[0]

        # in case no collection found return None
        # it is probably just single file
        if not collections:
            return

        # we expect only one collection
        collection = collections[0]

        self.log.debug("__ collection: {}".format(collection))

        if collection.is_contiguous():
            return self._format_collection(collection)

        # add `[` in front to make sure it want capture
        # shot name with the same number
        number_from_path = self._separate_number(feed_basename, feed_ext)
        search_number_pattern = "[" + number_from_path
        # convert to multiple collections
        _continues_colls = collection.separate()
        for _coll in _continues_colls:
            coll_to_text = self._format_collection(_coll, len(number_from_path))
            self.log.debug("__ coll_to_text: {}".format(coll_to_text))
            if search_number_pattern in coll_to_text:
                return coll_to_text

    @staticmethod
    def _format_collection(collection, padding=None):
        padding = padding or collection.padding
        # if no holes then return collection
        head = collection.format("{head}")
        tail = collection.format("{tail}")
        range_template = "[{{:0{0}d}}-{{:0{0}d}}]".format(
            padding)
        ranges = range_template.format(
            min(collection.indexes),
            max(collection.indexes)
        )
        # if no holes then return collection
        return "{}{}{}".format(head, ranges, tail)

    def _separate_file_head(self, basename, extension):
        """ Get only head with out sequence and extension

        Args:
            basename (str): file base name
            extension (str): file extension

        Returns:
            str: file head
        """
        # in case sequence file
        found = re.findall(
            r"(.*)[._][\d]*(?=.{})".format(extension),
            basename,
        )
        if found:
            return found.pop()

        # in case single file
        name, ext = os.path.splitext(basename)

        if extension == ext[1:]:
            return name

    def _separate_number(self, basename, extension):
        """ Get only sequence number as string

        Args:
            basename (str): file base name
            extension (str): file extension

        Returns:
            str: number with padding
        """
        # in case sequence file
        found = re.findall(
            r"[._]([\d]*)(?=.{})".format(extension),
            basename,
        )
        if found:
            return found.pop()

    @property
    def clip_data(self):
        """Clip's xml clip data

        Returns:
            xml.etree.ElementTree: xml data
        """
        return self._clip_data

    @clip_data.setter
    def clip_data(self, data):
        self._clip_data = data

    @property
    def start_frame(self):
        """ Clip's starting frame found in timecode

        Returns:
            int: number of frames
        """
        return self._start_frame

    @start_frame.setter
    def start_frame(self, number):
        self._start_frame = int(number)

    @property
    def fps(self):
        """ Clip's frame rate

        Returns:
            float: frame rate
        """
        return self._fps

    @fps.setter
    def fps(self, fl_number):
        self._fps = float(fl_number)

    @property
    def drop_mode(self):
        """ Clip's drop frame mode

        Returns:
            str: drop frame flag
        """
        return self._drop_mode

    @drop_mode.setter
    def drop_mode(self, text):
        self._drop_mode = str(text)

    @property
    def file_pattern(self):
        """Clips file patter

        Returns:
            str: file pattern. ex. file.[1-2].exr
        """
        return self._file_pattern

    @file_pattern.setter
    def file_pattern(self, fpattern):
        self._file_pattern = fpattern

    def _validate_media_script_path(self):
        if not os.path.isfile(self.MEDIA_SCRIPT_PATH):
            raise IOError("Media Scirpt does not exist: `{}`".format(
                self.MEDIA_SCRIPT_PATH))

    def _generate_media_info_file(self, fpath, feed_ext, feed_dir):
        """ Generate media info xml .clip file

        Args:
            fpath (str): .clip file path
            feed_ext (str): file extension to be filtered
            feed_dir (str): look up directory

        Raises:
            TypeError: Type error if it fails
        """
        # Create cmd arguments for gettig xml file info file
        cmd_args = [
            self.MEDIA_SCRIPT_PATH,
            "-e", feed_ext,
            "-o", fpath,
            feed_dir
        ]

        try:
            # execute creation of clip xml template data
            openpype.run_subprocess(cmd_args)
        except TypeError as error:
            raise TypeError(
                "Error creating `{}` due: {}".format(fpath, error))

    def _make_single_clip_media_info(self, fpath, feed_basename, path_pattern):
        """ Separate only relative clip object form .clip file

        Args:
            fpath (str): clip file path
            feed_basename (str): search basename
            path_pattern (str): search file pattern (file.[1-2].exr)

        Raises:
            ET.ParseError: if nothing found

        Returns:
            ET.Element: xml element data of matching clip
        """
        with open(fpath) as f:
            lines = f.readlines()
            _added_root = itertools.chain(
                "<root>", deepcopy(lines)[1:], "</root>")
            new_root = ET.fromstringlist(_added_root)

        # find the clip which is matching to my input name
        xml_clips = new_root.findall("clip")
        matching_clip = None
        for xml_clip in xml_clips:
            clip_name = xml_clip.find("name").text
            self.log.debug("__ clip_name: `{}`".format(clip_name))
            if clip_name not in feed_basename:
                continue

            # test path pattern
            for out_track in xml_clip.iter("track"):
                for out_feed in out_track.iter("feed"):
                    for span in out_feed.iter("span"):
                        # start frame
                        span_path = span.find("path")
                        self.log.debug(
                            "__ span_path.text: {}, path_pattern: {}".format(
                                span_path.text, path_pattern
                            )
                        )
                        if path_pattern in span_path.text:
                            matching_clip = xml_clip

        if matching_clip is None:
            # return warning there is missing clip
            raise ET.ParseError(
                "Missing clip in `{}`. Available clips {}".format(
                    feed_basename, [
                        xml_clip.find("name").text
                        for xml_clip in xml_clips
                    ]
                ))

        return matching_clip

    def _get_time_info_from_origin(self, xml_data):
        """Set time info to class attributes

        Args:
            xml_data (ET.Element): clip data
        """
        try:
            for out_track in xml_data.iter('track'):
                for out_feed in out_track.iter('feed'):
                    # start frame
                    out_feed_nb_ticks_obj = out_feed.find(
                        'startTimecode/nbTicks')
                    self.start_frame = out_feed_nb_ticks_obj.text

                    # fps
                    out_feed_fps_obj = out_feed.find(
                        'startTimecode/rate')
                    self.fps = out_feed_fps_obj.text

                    # drop frame mode
                    out_feed_drop_mode_obj = out_feed.find(
                        'startTimecode/dropMode')
                    self.drop_mode = out_feed_drop_mode_obj.text
                    break
        except Exception as msg:
            self.log.warning(msg)

    @staticmethod
    def write_clip_data_to_file(fpath, xml_element_data):
        """ Write xml element of clip data to file

        Args:
            fpath (string): file path
            xml_element_data (xml.etree.ElementTree.Element): xml data

        Raises:
            IOError: If data could not be written to file
        """
        try:
            # save it as new file
            tree = cET.ElementTree(xml_element_data)
            tree.write(
                fpath, xml_declaration=True,
                method='xml', encoding='UTF-8'
            )
        except IOError as error:
            raise IOError(
                "Not able to write data to file: {}".format(error))
