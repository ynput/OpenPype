import sys
from .utils import get_resolve_module
from pypeapp import Logger

log = Logger().get_logger(__name__, "resolve")

self = sys.modules[__name__]
self.pm = None


def get_project_manager():
    if not self.pm:
        resolve = get_resolve_module()
        self.pm = resolve.GetProjectManager()
    return self.pm


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
