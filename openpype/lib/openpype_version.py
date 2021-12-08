"""Lib access to OpenPypeVersion from igniter.

Access to logic from igniter is available only for OpenPype processes.
Is meant to be able check OpenPype versions for studio. The logic is dependent
on igniter's inner logic of versions.

Keep in mind that all functions except 'get_build_version' does not return
OpenPype version located in build but versions available in remote versions
repository or locally available.
"""

import sys


def get_OpenPypeVersion():
    """Access to OpenPypeVersion class stored in sys modules."""
    return sys.modules.get("OpenPypeVersion")


def op_version_control_available():
    """Check if current process has access to OpenPypeVersion."""
    if get_OpenPypeVersion() is None:
        return False
    return True


def get_build_version():
    """Get OpenPype version inside build.

    This version is not returned by any other functions here.
    """
    if op_version_control_available():
        return get_OpenPypeVersion().get_build_version()
    return None


def get_available_versions(*args, **kwargs):
    """Get list of available versions."""
    if op_version_control_available():
        return get_OpenPypeVersion().get_available_versions(
            *args, **kwargs
        )
    return None


def openpype_path_is_set():
    """OpenPype repository path is set in settings."""
    if op_version_control_available():
        return get_OpenPypeVersion().openpype_path_is_set()
    return None


def openpype_path_is_accessible():
    """OpenPype version repository path can be accessed."""
    if op_version_control_available():
        return get_OpenPypeVersion().openpype_path_is_accessible()
    return None


def get_local_versions(*args, **kwargs):
    """OpenPype versions available on this workstation."""
    if op_version_control_available():
        return get_OpenPypeVersion().get_local_versions(*args, **kwargs)
    return None


def get_remote_versions(*args, **kwargs):
    """OpenPype versions in repository path."""
    if op_version_control_available():
        return get_OpenPypeVersion().get_remote_versions(*args, **kwargs)
    return None


def get_latest_version(*args, **kwargs):
    """Get latest version from repository path."""
    if op_version_control_available():
        return get_OpenPypeVersion().get_latest_version(*args, **kwargs)
    return None


def get_expected_studio_version(staging=False):
    """Expected production or staging version in studio."""
    if op_version_control_available():
        return get_OpenPypeVersion().get_expected_studio_version(staging)
    return None
