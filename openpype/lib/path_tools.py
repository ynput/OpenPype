import os
import re
import abc
import json
import logging
import six
import platform

from openpype.settings import get_project_settings

from .anatomy import Anatomy
from .profiles_filtering import filter_profiles

log = logging.getLogger(__name__)


def create_hard_link(src_path, dst_path):
    """Create hardlink of file.

    Args:
        src_path(str): Full path to a file which is used as source for
            hardlink.
        dst_path(str): Full path to a file where a link of source will be
            added.
    """
    # Use `os.link` if is available
    #   - should be for all platforms with newer python versions
    if hasattr(os, "link"):
        os.link(src_path, dst_path)
        return

    # Windows implementation of hardlinks
    #   - used in Python 2
    if platform.system().lower() == "windows":
        import ctypes
        from ctypes.wintypes import BOOL
        CreateHardLink = ctypes.windll.kernel32.CreateHardLinkW
        CreateHardLink.argtypes = [
            ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_void_p
        ]
        CreateHardLink.restype = BOOL

        res = CreateHardLink(dst_path, src_path, None)
        if res == 0:
            raise ctypes.WinError()
        return
    # Raises not implemented error if gets here
    raise NotImplementedError(
        "Implementation of hardlink for current environment is missing."
    )


def _rreplace(s, a, b, n=1):
    """Replace a with b in string s from right side n times."""
    return b.join(s.rsplit(a, n))


def version_up(filepath):
    """Version up filepath to a new non-existing version.

    Parses for a version identifier like `_v001` or `.v001`
    When no version present _v001 is appended as suffix.

    Args:
        filepath (str): full url

    Returns:
        (str): filepath with increased version number

    """
    dirname = os.path.dirname(filepath)
    basename, ext = os.path.splitext(os.path.basename(filepath))

    regex = r"[._]v\d+"
    matches = re.findall(regex, str(basename), re.IGNORECASE)
    if not matches:
        log.info("Creating version...")
        new_label = "_v{version:03d}".format(version=1)
        new_basename = "{}{}".format(basename, new_label)
    else:
        label = matches[-1]
        version = re.search(r"\d+", label).group()
        padding = len(version)

        new_version = int(version) + 1
        new_version = '{version:0{padding}d}'.format(version=new_version,
                                                     padding=padding)
        new_label = label.replace(version, new_version, 1)
        new_basename = _rreplace(basename, label, new_label)
    new_filename = "{}{}".format(new_basename, ext)
    new_filename = os.path.join(dirname, new_filename)
    new_filename = os.path.normpath(new_filename)

    if new_filename == filepath:
        raise RuntimeError("Created path is the same as current file,"
                           "this is a bug")

    # We check for version clashes against the current file for any file
    # that matches completely in name up to the {version} label found. Thus
    # if source file was test_v001_test.txt we want to also check clashes
    # against test_v002.txt but do want to preserve the part after the version
    # label for our new filename
    clash_basename = new_basename
    if not clash_basename.endswith(new_label):
        index = (clash_basename.find(new_label))
        index += len(new_label)
        clash_basename = clash_basename[:index]

    for file in os.listdir(dirname):
        if file.endswith(ext) and file.startswith(clash_basename):
            log.info("Skipping existing version %s" % new_label)
            return version_up(new_filename)

    log.info("New version %s" % new_label)
    return new_filename


def get_version_from_path(file):
    """Find version number in file path string.

    Args:
        file (string): file path

    Returns:
        v: version number in string ('001')

    """
    pattern = re.compile(r"[\._]v([0-9]+)", re.IGNORECASE)
    try:
        return pattern.findall(file)[-1]
    except IndexError:
        log.error(
            "templates:get_version_from_workfile:"
            "`{}` missing version string."
            "Example `v004`".format(file)
        )


def get_last_version_from_path(path_dir, filter):
    """Find last version of given directory content.

    Args:
        path_dir (string): directory path
        filter (list): list of strings used as file name filter

    Returns:
        string: file name with last version

    Example:
        last_version_file = get_last_version_from_path(
            "/project/shots/shot01/work", ["shot01", "compositing", "nk"])
    """
    assert os.path.isdir(path_dir), "`path_dir` argument needs to be directory"
    assert isinstance(filter, list) and (
        len(filter) != 0), "`filter` argument needs to be list and not empty"

    filtred_files = list()

    # form regex for filtering
    pattern = r".*".join(filter)

    for file in os.listdir(path_dir):
        if not re.findall(pattern, file):
            continue
        filtred_files.append(file)

    if filtred_files:
        sorted(filtred_files)
        return filtred_files[-1]

    return None


def compute_paths(basic_paths_items, project_root):
    pattern_array = re.compile(r"\[.*\]")
    project_root_key = "__project_root__"
    output = []
    for path_items in basic_paths_items:
        clean_items = []
        for path_item in path_items:
            matches = re.findall(pattern_array, path_item)
            if len(matches) > 0:
                path_item = path_item.replace(matches[0], "")
            if path_item == project_root_key:
                path_item = project_root
            clean_items.append(path_item)
        output.append(os.path.normpath(os.path.sep.join(clean_items)))
    return output


def create_project_folders(basic_paths, project_name):
    anatomy = Anatomy(project_name)
    roots_paths = []
    if isinstance(anatomy.roots, dict):
        for root in anatomy.roots.values():
            roots_paths.append(root.value)
    else:
        roots_paths.append(anatomy.roots.value)

    for root_path in roots_paths:
        project_root = os.path.join(root_path, project_name)
        full_paths = compute_paths(basic_paths, project_root)
        # Create folders
        for path in full_paths:
            full_path = path.format(project_root=project_root)
            if os.path.exists(full_path):
                log.debug(
                    "Folder already exists: {}".format(full_path)
                )
            else:
                log.debug("Creating folder: {}".format(full_path))
                os.makedirs(full_path)


def _list_path_items(folder_structure):
    output = []
    for key, value in folder_structure.items():
        if not value:
            output.append(key)
        else:
            paths = _list_path_items(value)
            for path in paths:
                if not isinstance(path, (list, tuple)):
                    path = [path]

                item = [key]
                item.extend(path)
                output.append(item)

    return output


def get_project_basic_paths(project_name):
    project_settings = get_project_settings(project_name)
    folder_structure = (
        project_settings["global"]["project_folder_structure"]
    )
    if not folder_structure:
        return []

    if isinstance(folder_structure, str):
        folder_structure = json.loads(folder_structure)
    return _list_path_items(folder_structure)


def create_workdir_extra_folders(
    workdir, host_name, task_type, task_name, project_name,
    project_settings=None
):
    """Create extra folders in work directory based on context.

    Args:
        workdir (str): Path to workdir where workfiles is stored.
        host_name (str): Name of host implementation.
        task_type (str): Type of task for which extra folders should be
            created.
        task_name (str): Name of task for which extra folders should be
            created.
        project_name (str): Name of project on which task is.
        project_settings (dict): Prepared project settings. Are loaded if not
            passed.
    """
    # Load project settings if not set
    if not project_settings:
        project_settings = get_project_settings(project_name)

    # Load extra folders profiles
    extra_folders_profiles = (
        project_settings["global"]["tools"]["Workfiles"]["extra_folders"]
    )
    # Skip if are empty
    if not extra_folders_profiles:
        return

    # Prepare profiles filters
    filter_data = {
        "task_types": task_type,
        "task_names": task_name,
        "hosts": host_name
    }
    profile = filter_profiles(extra_folders_profiles, filter_data)
    if profile is None:
        return

    for subfolder in profile["folders"]:
        # Make sure backslashes are converted to forwards slashes
        #   and does not start with slash
        subfolder = subfolder.replace("\\", "/").lstrip("/")
        # Skip empty strings
        if not subfolder:
            continue

        fullpath = os.path.join(workdir, subfolder)
        if not os.path.exists(fullpath):
            os.makedirs(fullpath)


@six.add_metaclass(abc.ABCMeta)
class HostDirmap:
    """
        Abstract class for running dirmap on a workfile in a host.

        Dirmap is used to translate paths inside of host workfile from one
        OS to another. (Eg. arstist created workfile on Win, different artists
        opens same file on Linux.)

        Expects methods to be implemented inside of host:
            on_dirmap_enabled: run host code for enabling dirmap
            do_dirmap: run host code to do actual remapping
    """
    def __init__(self, host_name, project_settings, sync_module=None):
        self.host_name = host_name
        self.project_settings = project_settings
        self.sync_module = sync_module  # to limit reinit of Modules

        self._mapping = None  # cache mapping

    @abc.abstractmethod
    def on_enable_dirmap(self):
        """
            Run host dependent operation for enabling dirmap if necessary.
        """

    @abc.abstractmethod
    def dirmap_routine(self, source_path, destination_path):
        """
            Run host dependent remapping from source_path to destination_path
        """

    def process_dirmap(self):
        # type: (dict) -> None
        """Go through all paths in Settings and set them using `dirmap`.

            If artists has Site Sync enabled, take dirmap mapping directly from
            Local Settings when artist is syncing workfile locally.

        Args:
            project_settings (dict): Settings for current project.

        """
        if not self._mapping:
            self._mapping = self.get_mappings(self.project_settings)
        if not self._mapping:
            return

        log.info("Processing directory mapping ...")
        self.on_enable_dirmap()
        log.info("mapping:: {}".format(self._mapping))

        for k, sp in enumerate(self._mapping["source-path"]):
            try:
                print("{} -> {}".format(sp,
                                        self._mapping["destination-path"][k]))
                self.dirmap_routine(sp,
                                    self._mapping["destination-path"][k])
            except IndexError:
                # missing corresponding destination path
                log.error(("invalid dirmap mapping, missing corresponding"
                           " destination directory."))
                break
            except RuntimeError:
                log.error("invalid path {} -> {}, mapping not registered".format(  # noqa: E501
                    sp, self._mapping["destination-path"][k]
                ))
                continue

    def get_mappings(self, project_settings):
        """Get translation from source-path to destination-path.

            It checks if Site Sync is enabled and user chose to use local
            site, in that case configuration in Local Settings takes precedence
        """
        local_mapping = self._get_local_sync_dirmap(project_settings)
        dirmap_label = "{}-dirmap".format(self.host_name)
        if not self.project_settings[self.host_name].get(dirmap_label) and \
                not local_mapping:
            return []
        mapping = local_mapping or \
            self.project_settings[self.host_name][dirmap_label]["paths"] or {}
        enbled = self.project_settings[self.host_name][dirmap_label]["enabled"]
        mapping_enabled = enbled or bool(local_mapping)

        if not mapping or not mapping_enabled or \
                not mapping.get("destination-path") or \
                not mapping.get("source-path"):
            return []
        return mapping

    def _get_local_sync_dirmap(self, project_settings):
        """
            Returns dirmap if synch to local project is enabled.

            Only valid mapping is from roots of remote site to local site set
            in Local Settings.

            Args:
                project_settings (dict)
            Returns:
                dict : { "source-path": [XXX], "destination-path": [YYYY]}
        """
        import json
        mapping = {}

        if not project_settings["global"]["sync_server"]["enabled"]:
            return mapping

        from openpype.settings.lib import get_site_local_overrides

        if not self.sync_module:
            from openpype.modules import ModulesManager
            manager = ModulesManager()
            self.sync_module = manager.modules_by_name["sync_server"]

        project_name = os.getenv("AVALON_PROJECT")

        active_site = self.sync_module.get_local_normalized_site(
            self.sync_module.get_active_site(project_name))
        remote_site = self.sync_module.get_local_normalized_site(
            self.sync_module.get_remote_site(project_name))
        log.debug("active {} - remote {}".format(active_site, remote_site))

        if active_site == "local" \
                and project_name in self.sync_module.get_enabled_projects()\
                and active_site != remote_site:

            sync_settings = self.sync_module.get_sync_project_setting(
                os.getenv("AVALON_PROJECT"), exclude_locals=False,
                cached=False)

            active_overrides = get_site_local_overrides(
                os.getenv("AVALON_PROJECT"), active_site)
            remote_overrides = get_site_local_overrides(
                os.getenv("AVALON_PROJECT"), remote_site)

            log.debug("local overrides".format(active_overrides))
            log.debug("remote overrides".format(remote_overrides))
            for root_name, active_site_dir in active_overrides.items():
                remote_site_dir = remote_overrides.get(root_name) or\
                    sync_settings["sites"][remote_site]["root"][root_name]
                if os.path.isdir(active_site_dir):
                    if not mapping.get("destination-path"):
                        mapping["destination-path"] = []
                    mapping["destination-path"].append(active_site_dir)

                    if not mapping.get("source-path"):
                        mapping["source-path"] = []
                    mapping["source-path"].append(remote_site_dir)

            log.debug("local sync mapping:: {}".format(mapping))
        return mapping
