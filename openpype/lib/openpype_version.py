"""Lib access to OpenPypeVersion from igniter.

Access to logic from igniter is available only for OpenPype processes.
Is meant to be able check OpenPype versions for studio. The logic is dependent
on igniter's logic of processing.
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
    if op_version_control_available():
        return get_OpenPypeVersion().openpype_path_is_set()
    return None


def openpype_path_is_accessible():
    if op_version_control_available():
        return get_OpenPypeVersion().openpype_path_is_accessible()
    return None


def get_local_versions(*args, **kwargs):
    if op_version_control_available():
        return get_OpenPypeVersion().get_local_versions(*args, **kwargs)
    return None


def get_remote_versions(*args, **kwargs):
    if op_version_control_available():
        return get_OpenPypeVersion().get_remote_versions(*args, **kwargs)
    return None


def get_latest_version(*args, **kwargs):
    if op_version_control_available():
        return get_OpenPypeVersion().get_latest_version(*args, **kwargs)
    return None


def get_current_production_version():
    if op_version_control_available():
        return get_OpenPypeVersion().get_production_version()
    return None


def get_current_staging_version():
    if op_version_control_available():
        return get_OpenPypeVersion().get_staging_version()
    return None
