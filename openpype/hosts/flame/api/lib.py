import sys
import os
import pickle
import contextlib
from pprint import pformat

from openpype.api import Logger

log = Logger().get_logger(__name__)


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
        self.load_prefs()

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


@contextlib.contextmanager
def maintain_current_timeline(to_timeline, from_timeline=None):
    """Maintain current timeline selection during context

    Attributes:
        from_timeline (resolve.Timeline)[optional]:
    Example:
        >>> print(from_timeline.GetName())
        timeline1
        >>> print(to_timeline.GetName())
        timeline2

        >>> with maintain_current_timeline(to_timeline):
        ...     print(get_current_sequence().GetName())
        timeline2

        >>> print(get_current_sequence().GetName())
        timeline1
    """
    # todo: this is still Resolve's implementation
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


def create_bin(name, root=None):
    # TODO: create_bin
    return


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
