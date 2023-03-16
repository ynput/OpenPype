import six

from . backends.perforce.api import P4PathDateData
from . lib import get_active_version_control_backend
from . lib import is_version_control_enabled
from typing import Any
from typing import overload
from typing import Sequence

if six.PY2:
    import pathlib2 as pathlib
else:
    import pathlib


@overload
def checked_out_by(
    path: pathlib.Path | str, other_users_only: bool = False
) -> list[str] | None:
    ...


@overload
def checked_out_by(
    path: Sequence[pathlib.Path | str], other_users_only: bool = False
) -> dict[str, list[str] | None]:
    ...


@overload
def get_server_version(path: pathlib.Path | str) -> int | None:
    """
    Get the current server revision numbers for the given path(s)

    Arguments:
    ----------
        - `path`: The file path(s) to get the server revision of.

    Returns:
    --------
        - If a single file is provided:
            The server version number. `None` if the file does not exist on the server.
        - If a list of files are provided:
            A dictionary where each key is the path and each value is
            the server version number or `None` if the file does not exist on the server.
    """
    ...


@overload
def get_server_version(path: Sequence[pathlib.Path | str]) -> dict[str, int | None]:
    ...


@overload
def get_local_version(path: pathlib.Path | str) -> int | None:
    """
    Get the current local (client) revision numbers for the given path(s)

    Arguments:
    ----------
        - `path`: The file path(s) to get the client revision of.

    Returns:
    --------
        - If a single file is provided:
            The local version number. Returns `0` if the file does not exist locally
            or `None` if the file does not exist on the server.
        - If a list of files are provided:
            A dictionary where each key is the path and each value is
            the local version number or `0` if the file does not exist locally
            or `None` if the file does not exist on the server.
    """
    ...


@overload
def get_local_version(path: Sequence[pathlib.Path | str]) -> dict[str, int | None]:
    ...


@overload
def get_version_info(path: pathlib.Path | str) -> tuple[int | None, int | None]:
    """
    Get client and server versions for the given path(s).

    Arguments:
    ----------
        - `path`: The file path(s) to get the versions of.

    Returns:
    --------
        - If a single file:
            A tuple with the client and server versions. Values are None if the file
            does not exist on the server.
        - If a list of files:
            A dictionary where each key is the path and each value is
            a tuple with the client and server versions. Values are None if the file
            does not exist on the server.
    """
    ...


@overload
def get_version_info(path: Sequence[pathlib.Path | str]) -> dict[str, tuple[int | None, int | None]]:
    ...


@overload
def is_checkedout(path: pathlib.Path | str) -> bool | None:
    ...


@overload
def is_checkedout(path: Sequence[pathlib.Path | str]) -> dict[str, bool | None]:
    ...


@overload
def is_latest_version(path: pathlib.Path | str) -> bool | None:
    ...


@overload
def is_latest_version(path: Sequence[pathlib.Path | str]) -> dict[str, bool | None]:
    ...


@overload
def exists_on_server(path: pathlib.Path | str) -> bool:
    ...


@overload
def exists_on_server(path: Sequence[pathlib.Path | str]) -> dict[str, bool]:
    ...


@overload
def sync_latest_version(path: pathlib.Path | str) -> bool | None:
    ...


@overload
def sync_latest_version(path: Sequence[pathlib.Path | str]) -> dict[str, bool | None]:
    ...


@overload
def sync_to_version(path: pathlib.Path | str, version: int) -> bool | None:
    ...


@overload
def sync_to_version(path: Sequence[pathlib.Path | str], version: int) -> dict[str, bool | None]:
    ...


@overload
def add(path: pathlib.Path | str, comment: str = "") -> bool:
    ...


@overload
def add(path: Sequence[pathlib.Path | str], comment: str = "") -> dict[str, bool]:
    ...


def add_to_change_list(path: Sequence[pathlib.Path | str], comment: str = "") -> dict[str, bool]:
    """
    Add the given path(s) to the existing change list
    with the given description.

    Arguments:
    ----------
        - `path`: The path(s) to add.
        - `description` : The description of the change list to add the
            file(s) to.
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        `True` if paths where successfully added, `False` if not.
    """
    ...


@overload
def checkout(path: pathlib.Path | str, comment: str = "") -> bool:
    ...


@overload
def checkout(path: Sequence[pathlib.Path | str], comment: str = "") -> dict[str, bool]:
    ...


@overload
def revert(path: pathlib.Path | str, comment: str = "") -> bool:
    ...


@overload
def revert(path: Sequence[pathlib.Path | str], comment: str = "") -> dict[str, bool]:
    ...


def move(path: pathlib.Path | str, new_path: pathlib.Path | str, change_description: str | None = None) -> bool | None:
    ...


def get_existing_change_list(comment):
    # type: (str) -> dict[str, Any] | None
    ...


@overload
def get_newest_file_in_folder(
    path: pathlib.Path | str,
    name_pattern: str | None = None,
    extensions: str | None = None
) -> pathlib.Path | None:
    ...


@overload
def get_newest_file_in_folder(
    path: Sequence[pathlib.Path | str],
    name_pattern: str | None = None,
    extensions: str | None = None
) -> dict[str, pathlib.Path | None]:
    ...


@overload
def get_files_in_folder_in_date_order(
    path: pathlib.Path | str,
    name_pattern: str | None = None,
    extensions: str | None = None
) -> list[pathlib.Path] | None:
    ...


@overload
def get_files_in_folder_in_date_order(
    path: Sequence[pathlib.Path | str],
    name_pattern: str | None = None,
    extensions: str | None = None
) -> dict[str, list[pathlib.Path] | None]:
    ...


def submit_change_list(comment):
    # type: (str) -> int | None
    ...


def update_change_list_description(comment, new_comment):
    # type: (str, str) -> bool
    ...


def get_change_list_description():
    # type: () -> str
    ...


def get_change_list_description_with_tags(description):
    # type: (str) -> str
    """
    Get the current change list but with tags ([tag1][tag2]) as a prefix.
    This is the convention for submitting files to perforce for use with
    Unreal Game Sync.
    """
    ...


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
