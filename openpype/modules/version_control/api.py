from . lib import get_active_version_control_backend
from . lib import is_version_control_enabled
from . lib import NoActiveVersionControlError
from . lib import VersionControlDisabledError

import pathlib

_typing = False
if _typing:
    import datetime

    from . import backends
    from typing import Any
    from typing import Union
    from typing import Sequence

    T_P4PATH = Union[pathlib.Path, str, Sequence[Union[pathlib.Path, str]]]
del _typing


_active_backend = None  # type: backends.abstract.VersionControl


def _with_active_backend(function):
    def wrapper(*args, **kwargs):
        global _active_backend
        try:
            _active_backend = _active_backend or get_active_version_control_backend()
        except (VersionControlDisabledError, NoActiveVersionControlError):
            pass

        return function(*args, **kwargs)

    return wrapper


@_with_active_backend
def get_server_version(path):
    # type: (T_P4PATH) -> int
    if not _active_backend:
        return 0

    return _active_backend.get_server_version(path)


@_with_active_backend
def get_local_version(path):
    # type: (T_P4PATH) -> int | None
    if not _active_backend:
        return

    return _active_backend.get_local_version(path)


@_with_active_backend
def get_version_info(path):
    # type: (T_P4PATH) -> tuple[int | None, int | None]
    if not _active_backend:
        return (None, None)

    return _active_backend.get_version_info(path)


@_with_active_backend
def is_checkedout(path):
    # type: (T_P4PATH) -> bool | None
    if not _active_backend:
        return

    return _active_backend.is_checkedout(path)


@_with_active_backend
def is_latest_version(path):
    # type: (T_P4PATH) -> bool | None
    if not _active_backend:
        return

    return _active_backend.is_latest_version(path)


@_with_active_backend
def exists_on_server(path):
    # type: (T_P4PATH) -> bool
    if not _active_backend:
        return True

    return _active_backend.exists_on_server(path)


@_with_active_backend
def sync_latest_version(path):
    # type: (T_P4PATH) -> bool
    if not _active_backend:
        return True

    return _active_backend.sync_latest_version(path)


@_with_active_backend
def sync_to_version(path, version):
    # type: (T_P4PATH, int) -> bool
    if not _active_backend:
        return True

    return _active_backend.sync_to_version(path, version)


@_with_active_backend
def add(path, comment=""):
    # type: (T_P4PATH, str) -> bool
    if not _active_backend:
        return True

    return _active_backend.add(path, comment=comment)


@_with_active_backend
def add_to_change_list(path, comment=""):
    # type: (T_P4PATH, str) -> bool
    if not _active_backend:
        return True

    return _active_backend.add_to_change_list(path, comment=comment)


@_with_active_backend
def checkout(path, comment=""):
    # type: (T_P4PATH, str) -> bool

    if not _active_backend:
        return True

    return _active_backend.checkout(path, comment=comment)


@_with_active_backend
def revert(path):
    # type: (T_P4PATH) -> bool

    if not _active_backend:
        return True

    return _active_backend.revert(path)


@_with_active_backend
def move(path, new_path, change_description=None):
    # type: (T_P4PATH, T_P4PATH, str | None) -> bool

    if not _active_backend:
        return True

    return _active_backend.move(path, new_path, change_description=change_description)


@_with_active_backend
def checked_out_by(path, other_users_only=False):
    # type: (T_P4PATH, bool) -> list[str] | None

    if not _active_backend:
        return

    return _active_backend.checked_out_by(path, other_users_only=other_users_only)


@_with_active_backend
def get_existing_change_list(comment):
    # type: (str) -> dict[str, Any] | None
    if not _active_backend:
        return {}

    return _active_backend.get_existing_change_list(comment)


@_with_active_backend
def get_newest_file_in_folder(path, name_pattern=None, extensions=None):
    # type: (T_P4PATH, str | None, Sequence[str] | None) -> pathlib.Path | None
    if not _active_backend:
        return

    return _active_backend.get_newest_file_in_folder(path, name_pattern=name_pattern, extensions=extensions)


@_with_active_backend
def get_files_in_folder_in_date_order(path, name_pattern=None, extensions=None):
    # type: (T_P4PATH, str | None, Sequence[str] | None) -> list[tuple[pathlib.Path, datetime.datetime]] | None
    if not _active_backend:
        return

    return _active_backend.get_files_in_folder_in_date_order(path, name_pattern=name_pattern, extensions=extensions)


@_with_active_backend
def submit_change_list(comment):
    # type: (str) -> int | None
    if not _active_backend:
        return True

    return _active_backend.submit_change_list(comment)


@_with_active_backend
def update_change_list_description(comment, new_comment):
    # type: (str, str) -> bool
    if not _active_backend:
        return True

    return _active_backend.update_change_list_description(comment, new_comment)


@_with_active_backend
def get_change_list_description():
    # type: () -> str
    if not _active_backend:
        return ""

    return _active_backend.change_list_description


@_with_active_backend
def get_change_list_description_with_tags(description):
    # type: (str) -> str
    """
    Get the current change list but with tags ([tag1][tag2]) as a prefix.
    This is the convention for submitting files to perforce for use with
    Unreal Game Sync.
    """
    global _active_backend
    if not _active_backend:
        return ""

    _active_backend.change_list_description = description
    return _active_backend.change_list_description


__all__ = (
    "get_active_version_control_backend",
    "is_version_control_enabled",
    "get_server_version",
    "get_local_version",
    "is_latest_version",
    "exists_on_server",
    "sync_latest_version",
    "add",
    "checkout",
    "get_existing_change_list",
    "submit_change_list",
    "update_change_list_description",
)
