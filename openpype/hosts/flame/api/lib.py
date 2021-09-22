import sys
import json
import re
import os
import pickle
import contextlib
from pprint import pprint, pformat
from opentimelineio import opentime
import openpype


# from ..otio import davinci_export as otio_export

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


class FlameAppFramework(object):
    # flameAppFramework class takes care of preferences

    class prefs_dict(dict):
        # subclass of a dict() in order to directly link it
        # to main framework prefs dictionaries
        # when accessed directly it will operate on a dictionary under a "name"
        # key in master dictionary.
        # master = {}
        # p = prefs(master, "app_name")
        # p["key"] = "value"
        # master - {"app_name": {"key", "value"}}

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

        def pop(self, k, v=object()):
            if v is object():
                return self.master[self.name].pop(k)
            return self.master[self.name].pop(k, v)

        def update(self, mapping=(), **kwargs):
            self.master[self.name].update(mapping, **kwargs)

        def __contains__(self, k):
            return self.master[self.name].__contains__(k)

        def copy(self): # don"t delegate w/ super - dict.copy() -> dict :(
            return type(self)(self)

        def keys(self):
            return self.master[self.name].keys()

        @classmethod
        def fromkeys(cls, keys, v=None):
            return cls.master[cls.name].fromkeys(keys, v)

        def __repr__(self):
            return "{0}({1})".format(type(self).__name__, self.master[self.name].__repr__())

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
        except:
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
                    self.bundle_name)
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

    def load_prefs(self):
        prefix = self.prefs_folder + os.path.sep + self.bundle_name
        prefs_file_path = (prefix + "." + self.flame_user_name + "."
                           + self.flame_project_name + ".prefs")
        prefs_user_file_path = (prefix + "." + self.flame_user_name
                                + ".prefs")
        prefs_global_file_path = prefix + ".prefs"

        try:
            with open(prefs_file_path, "r") as prefs_file:
                self.prefs = pickle.load(prefs_file)

            self.log.info("preferences loaded from {}".format(prefs_file_path))
            self.log.info("preferences contents:\n" + pformat(self.prefs))
        except:
            self.log.info("unable to load preferences from {}".format(
                prefs_file_path))

        try:
            with open(prefs_user_file_path, "r") as prefs_file:
                self.prefs_user = pickle.load(prefs_file)
            self.log.info("preferences loaded from {}".format(
                prefs_user_file_path))
            self.log.info("preferences contents:\n" + pformat(self.prefs_user))
        except:
            self.log.info("unable to load preferences from {}".format(
                prefs_user_file_path))

        try:
            with open(prefs_global_file_path, "r") as prefs_file:
                self.prefs_global = pickle.load(prefs_file)
            self.log.info("preferences loaded from {}".format(
                prefs_global_file_path))
            self.log.info("preferences contents:\n" + pformat(self.prefs_global))

        except:
            self.log.info("unable to load preferences from {}".format(
                prefs_global_file_path))

        return True

    def save_prefs(self):
        import pickle

        if not os.path.isdir(self.prefs_folder):
            try:
                os.makedirs(self.prefs_folder)
            except:
                self.log.info("unable to create folder {}".format(
                    self.prefs_folder))
                return False

        prefix = self.prefs_folder + os.path.sep + self.bundle_name
        prefs_file_path = prefix + "." + self.flame_user_name + "." + self.flame_project_name + ".prefs"
        prefs_user_file_path = prefix + "." + self.flame_user_name  + ".prefs"
        prefs_global_file_path = prefix + ".prefs"

        try:
            prefs_file = open(prefs_file_path, "w")
            pickle.dump(self.prefs, prefs_file)
            prefs_file.close()
            self.log.info("preferences saved to {}".format(prefs_file_path))
            self.log.info("preferences contents:\n" + pformat(self.prefs))
        except:
            self.log.info("unable to save preferences to {}".format(prefs_file_path))

        try:
            prefs_file = open(prefs_user_file_path, "w")
            pickle.dump(self.prefs_user, prefs_file)
            prefs_file.close()
            self.log.info("preferences saved to {}".format(prefs_user_file_path))
            self.log.info("preferences contents:\n" + pformat(self.prefs_user))
        except:
            self.log.info("unable to save preferences to {}".format(prefs_user_file_path))

        try:
            prefs_file = open(prefs_global_file_path, "w")
            pickle.dump(self.prefs_global, prefs_file)
            prefs_file.close()
            self.log.info("preferences saved to {}".format(prefs_global_file_path))
            self.log.info("preferences contents:\n" + pformat(self.prefs_global))
        except:
            self.log.info("unable to save preferences to {}".format(prefs_global_file_path))

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


def create_bin(name, root=None):
    # TODO: create_bin
    return


def rescan_hooks():
    import flame
    try:
        flame.execute_shortcut('Rescan Python Hooks')
    except:
        pass
