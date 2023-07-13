import os
import subprocess

from ayon_common.utils import get_ayon_appdirs, get_ayon_launch_args


def get_local_dir(*subdirs):
    """Get product directory in user's home directory.

    Each user on machine have own local directory where are downloaded updates,
    addons etc.

    Returns:
        str: Path to product local directory.
    """

    if not subdirs:
        raise ValueError("Must fill dir_name if nothing else provided!")

    local_dir = get_ayon_appdirs(*subdirs)
    if not os.path.isdir(local_dir):
        try:
            os.makedirs(local_dir)
        except Exception:  # TODO fix exception
            raise RuntimeError(f"Cannot create {local_dir}")

    return local_dir


def get_addons_dir():
    """Directory where addon packages are stored.

    Path to addons is defined using python module 'appdirs' which

    The path is stored into environment variable 'AYON_ADDONS_DIR'.
    Value of environment variable can be overriden, but we highly recommended
    to use that option only for development purposes.

    Returns:
        str: Path to directory where addons should be downloaded.
    """

    addons_dir = os.environ.get("AYON_ADDONS_DIR")
    if not addons_dir:
        addons_dir = get_local_dir("addons")
        os.environ["AYON_ADDONS_DIR"] = addons_dir
    return addons_dir


def get_dependencies_dir():
    """Directory where dependency packages are stored.

    Path to addons is defined using python module 'appdirs' which

    The path is stored into environment variable 'AYON_DEPENDENCIES_DIR'.
    Value of environment variable can be overriden, but we highly recommended
    to use that option only for development purposes.

    Returns:
        str: Path to directory where dependency packages should be downloaded.
    """

    dependencies_dir = os.environ.get("AYON_DEPENDENCIES_DIR")
    if not dependencies_dir:
        dependencies_dir = get_local_dir("dependency_packages")
        os.environ["AYON_DEPENDENCIES_DIR"] = dependencies_dir
    return dependencies_dir


def show_missing_bundle_information(url, bundle_name=None):
    """Show missing bundle information window.

    This function should be called when server does not have set bundle for
    production or staging, or when bundle that should be used is not available
    on server.

    Using subprocess to show the dialog. Is blocking and is waiting until
    dialog is closed.

    Args:
        url (str): Server url where bundle is not set.
        bundle_name (Optional[str]): Name of bundle that was not found.
    """

    ui_dir = os.path.join(os.path.dirname(__file__), "ui")
    script_path = os.path.join(ui_dir, "missing_bundle_window.py")
    args = get_ayon_launch_args(script_path, "--skip-bootstrap", "--url", url)
    if bundle_name:
        args.extend(["--bundle", bundle_name])
    subprocess.call(args)
