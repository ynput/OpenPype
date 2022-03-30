import sys
import os
import re
import json
import pickle
import contextlib
from pprint import pformat
from .constants import (
    MARKER_COLOR,
    MARKER_DURATION,
    MARKER_NAME,
    COLOR_MAP,
    MARKER_PUBLISH_DEFAULT
)
from openpype.api import Logger

log = Logger.get_logger(__name__)

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
        segment_attrs_data[attr] = str(attr).replace("+", ":")

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
