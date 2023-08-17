
import Qt.QtCore as QtCore
import dataclasses
import datetime
import pathlib
import six

from . import p4_errors

from contextlib import contextmanager
from typing import Any
from typing import Iterator
from typing import Iterable
from typing import Union
from typing import overload
from typing_extensions import Literal

if six.PY2:
    import pathlib2 as pathlib
else:
    import pathlib


class P4ConnectionManagerSignaller(QtCore.QObject):
    connected: QtCore.SignalInstance = ...
    disconnected: QtCore.SignalInstance = ...


@dataclasses.dataclass(frozen=False)
class P4PathDateData:
    path: pathlib.Path | None = None
    date: datetime.datetime | None = None

    def set_data(self, path: pathlib.Path | None, date: datetime.datetime | None):
        ...


class P4ConnectionManager:
    _signaller: P4ConnectionManagerSignaller = ...

    @property
    def is_offline(self) -> bool:
        """ Flag denoting if the perforce server is offline.
        """
        ...

    @property
    def exceptions(self) -> p4_errors.P4Exceptions:
        """ Enum holding all exception types
        """
        ...

    @overload
    def add(
        self,
        path: str | pathlib.Path,
        change_description: str | None = None,
        workspace_override: str | None = None
    ) -> bool:
        """
        Add the given path(s) if they do not exists on the server already.

        Arguments:
        ----------
            - `path`: The path(s) to add
            - `change_description` (optional): If provided, the description of the
                change list to add the added file(s) to. If None, will add them
                to the default change list. Defaults to `None`
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

        Returns:
        --------
            If a single file is provided:
                `True` if successfully added, `False` if not.
            If a list of files are provided:
                A dictionary where each key is the path and each value is
                `True` if successfully added, `False` if not.
        """
        ...

    @overload
    def add(
        self,
        path: Iterable[str | pathlib.Path],
        change_description: str | None = None,
        workspace_override: str | None = None
    ) -> dict[str, bool]:
        """
        Add the given file if it does not exists on the server already.
        """
        ...

    def add_to_change_list(
        self,
        path: str | pathlib.Path | Iterable[str | pathlib.Path],
        description: str,
        workspace_override: str | None = None
    ) -> bool:
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
    def checkout(
        self,
        path: str | pathlib.Path,
        change_description: str | None = None,
        workspace_override: str | None = None
    ) -> bool:
        """
        Checkout the given path(s) if they exist on the server.

        Arguments:
        ----------
            - `path`: The path(s) to checkout
            - `change_description` (optional): If provided, the description of the
                change list to add the deleted file(s) to. If None, will add them
                to the default change list. Defaults to `None`
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

        Returns:
        --------
            If a single file is provided:
                `True` if successfully checked out, `False` if not.
            If a list of files are provided:
                A dictionary where each key is the path and each value is
                `True` if successfully checked out, `False` if not.
        """
        ...

    @overload
    def checkout(
        self,
        path: Iterable[str | pathlib.Path],
        change_description: str | None = None,
        workspace_override: str | None = None
    ) -> dict[str, bool]:
        ...

    def create_change_list(
        self,
        description: str,
        files: Iterable[str | pathlib.Path] | None = None,
        workspace_override: str | None = None
    ) -> bool:
        """
        Create a change list with the given description and optional files.

        Arguments:
        ----------
            - `description`: The change list description. If a change list
                already exists with this description, it will be used instead
                of creating a new one.
            - `files` (optional): Defines a list of files to add to the change list.
                Defaults to None
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

        Returns:
        --------
            `True` on success, `False` on Failure.
        """
        ...

    def create_workspace(self, name: str, root: str, stream: str) -> Any:
        """# Not functional"""
        ...

    @overload
    def delete(
        self,
        path: str | pathlib.Path,
        change_description: str | None = None,
        workspace_override: str | None = None
    ) -> bool:
        """
        Delete the given file(s) if they exists on the server.

        Note that the files will be deleted locally, but not from
        the server until their respective change list is submitted!

        Arguments:
        ----------
            - `path`: The file path(s) to delete from the server.
            - `change_description` (optional): If provided, the description of the
                change list to add the deleted file(s) to. If None, will add them
                to the default change list. Defaults to `None`
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

        Returns:
        --------
            - If a single file is provided:
                `True` if successfully deleted, `False` if not.
            - If a list of files are provided:
                A dictionary where each key is the path and each value is
                `True` if successfully deleted, `False` if not.
        """
        ...

    @overload
    def delete(
        self,
        path: Iterable[str | pathlib.Path],
        change_description: str | None = None,
        workspace_override: str | None = None
    ) -> list[bool]:
        ...

    def delete_change_list(
        self,
        description: str,
        force: bool = False,
        workspace_override: str = "",
    ) -> bool:
        """
        Delete a change list based on it's description.

        Arguments:
        ----------
            - `description`: The description of the change list to delete.
            - `force` (optional): If `True` - remove any files in the change list to the
                default change list before deleting. The default behaviour of P4 is to
                fail to delete a change list if it contains files. Defaults to `False`
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

        Returns:
        --------
            `True` if successfully deleted, `False` if not.
        """
        ...

    @overload
    def checked_out_by(
        self,
        path: str | pathlib.Path,
        other_users_only: bool = False,
        fstat_args: Iterable[str] | None = None,
        workspace_override: str | None = None
    ) -> list[str] | None:
        """
        Get a list of users that the given file(s) are checked out by.

        Arguments:
        ----------
            - `path`: The path(s) to query.
            - `other_users_only` (optional): If `True`, will not include current user
                in list of users with file checked out, if the file is checked out
                by the current user. Defaults to `True`
            - `fstat_args` (optional): If provided, a list of arguments to use
                when running the fstat command to run the checked out query with.
                Refer to the perforce docs for more information:
                https://www.perforce.com/manuals/cmdref/Content/CmdRef/p4_fstat.html
                Defaults to `None`
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

        Returns:
        --------
            If a single file is provided:
                A list of users who have the file checked out or
                `None` if the file is not checked out.
            If a list of files are provided:
                A dictionary where each key is the path and each value is
                a list of users who have the given file checked out or
                `None` if the given file is not checked out.
        """
        ...

    @overload
    def checked_out_by(
        self,
        path: Iterable[str | pathlib.Path],
        other_users_only: bool = False,
        fstat_args: Iterable[str] | None = None,
        workspace_override: str | None = None
    ) -> list[list[str] | None]:
        ...

    @overload
    def exists_on_server(
        self,
        path: str | pathlib.Path,
        workspace_override: str | None = None
    ) -> bool:
        """
        Query if the given path(s) exist on the server.

        Arguments:
        ----------
            - `path`: The path(s) to query.
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

        Returns:
        --------
            If a single file is provided:
                `True` if the path exists, `False` if not.
            If a list of files are provided:
                A dictionary where each key is the path and each value is
                `True` if the path exists, `False` if not.
        """
        ...

    @overload
    def exists_on_server(
        self,
        path: Iterable[str | pathlib.Path],
        workspace_override: str | None = None
    ) -> dict[str, bool]:
        ...

    @overload
    def get_attribute(
        self,
        path: str | pathlib.Path,
        name: str,
        default: Any = None,
        raise_error:bool = False,
        workspace_override: str | None = None
    ) -> Any:
        """
        Get the attribute from the given file(s).

        Arguments:
        ----------
            - `path`: The file path(s) to get the attribute on.
            - `name`: The name of the attribute to get.
            - `default` (optional): The default value to return if the file(s) do not
                have an attribute with the given name. Requires `raise_error` to be `False`
                Defaults to `None`
            - `raise_error` (optional): If `True` will raise `P4AttributeError` during the
                function call if a file does not have the attribute. This is immediate.
                If `False` will print the error but allow the function to complete, returning
                the object set in the `default` argument.
                Defaults to `False`
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

        Raises:
        -------
            If `raise_error` is True, the function will exit upon the first file without
            the given attribute, raising `P4AttributeError`

        Returns:
        --------
            - If a single file is provided:
                The value of the attribute if it exists. `default` value if it does not.
            - If a list of files are provided:
                A dictionary where each key is the path and each value is
                The value of the attribute if it exists. `default` value if it does not.
        """
        ...

    @overload
    def get_attribute(
        self,
        path: Iterable[str | pathlib.Path],
        name: str,
        default: Any = None,
        raise_error:bool = False,
        workspace_override: str | None = None
    ) -> dict[str, Any]:
        ...

    def get_client_root(self, workspace_override: str | None = None) -> str:
        """
        Get the local path root for the current workspace.

        Arguments:
        ----------
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully. Defaults to `None`

        Returns:
        --------
            A string of the local path root.
        """
        ...

    @overload
    def get_current_client_revision(
        self,
        path: str | pathlib.Path,
        workspace_override: str | None = None
    ) -> int | None:
        """
        Get the current client revision numbers for the given path(s)

        Arguments:
        ----------
            - `path`: The file path(s) to get the client revision of.
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

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
    def get_current_client_revision(
        self,
        path: Iterable[str | pathlib.Path], workspace_override: str | None = None
    ) -> dict[str, int | None]:
        ...

    @overload
    def get_current_revision_info(
        self,
        path: str | pathlib.Path,
        workspace_override: str | None = None
    ) -> tuple[int, int] | tuple[int, Literal[0]] | tuple[None, None]:
        """
        Get the current source and client revision numbers for the given path(s)

        Arguments:
        ----------
            - `path`: The file path(s) to get the client revision of.
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

        Returns:
        --------
            - If a single file is provided:
                A tuple containing the server and local version numbers.
                Returns a tuple`[<server_index>, 0]` if the file does not exist locally
                or `tuple[None, None]` if the file does not exist on the server.
            - If a list of files are provided:
                A dictionary where each key is the path and each value is
                a tuple containing the server and local version numbers.
                Returns a tuple`[<server_index>, 0]` if the file does not exist locally
                or `tuple[None, None]` if the file does not exist on the server.
        """
        ...

    @overload
    def get_current_revision_info(
        self,
        path: Iterable[str | pathlib.Path],
        workspace_override: str | None = None
    ) -> dict[str, tuple[int, int] | tuple[int, Literal[0]] | tuple[None, None]]:
        ...

    @overload
    def get_current_server_revision(
        self,
        path: str | pathlib.Path,
        workspace_override: str | None = None
    ) -> int | None:
        """
        Get the current server revision numbers for the given path(s)

        Arguments:
        ----------
            - `path`: The file path(s) to get the server revision of.
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

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
    def get_current_server_revision(
        self,
        path: Iterable[str | pathlib.Path],
        workspace_override: str | None = None
    ) -> dict[str, int | None]:
        ...

    def get_existing_change_list(
        self,
        description: str,
        workspace_override: str | None = None
    ) -> dict[str, Any] | None:
        """
        Get and existing changelist with the given description.

        Arguments:
        ----------
            - `description`: The change list description.
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

        Returns:
        --------
            - A dictionary describing the existing change list.
        """
        ...

    @overload
    def get_files(
        self,
        path: str | pathlib.Path,
        extension: str | None = None,
        include_all: bool = False,
        query_sub_folders: bool = False,
        workspace_override: str | None = None
    ) -> tuple[pathlib.Path]:
        """
        Get a list of files in the given folder(s).

        Arguments:
        ----------
            - `path`: The directory path(s) to get the sub-files of.
            - `extension` (optional): If provided, will filter the result by the extension type.
                Defaults  to `None`
            - `include_all` (optional): If `True`, will include deleted, purged, and archived files.
                If `False` only include files available for syncing or integration.
                Defaults  to `False`
            - `query_sub_folders` (optional): If `True, will get all sub-files of sub-folders.
                Defaults to `True`
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

        Returns:
        --------
            - If a single file is provided:
                A tuple with the sub-files of the given folder.
            - If a list of files are provided:
                A dictionary where each key is the path and each value is
                a tuple with the sub-files of the given folder.
        """
        ...

    @overload
    def get_files(
        self,
        path: str | pathlib.Path,
        extension: str | None = None,
        include_all: bool = False,
        query_sub_folders: bool = False,
        workspace_override: str | None = None
    ) -> dict[str, tuple[pathlib.Path]]:
        ...

    @overload
    def get_files_in_folder_in_date_order(
        self,
        path: str | pathlib.Path,
        name_pattern: str | None = None,
        extensions: Iterable[str] | None = None,
        workspace_override: str | None = None
    ) -> tuple[P4PathDateData, ...]:
        """
        Get a list of files in the given folder(s) in date order,
        oldest to newest.

        Arguments:
        ----------
            - `path`: The directory path(s) to get the sub-files of.
            - `name_pattern` (optional): A specific name pattern used to filter
                the returned files by name. If `None`, no files are filtered.
                Defaults to `None`
            - `extensions` (optional): A list of file extensions used to filter
                the returned files by. If `None` no files are filtered.
                Defaults to `None`
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

        Returns:
        --------
            - If a single file is provided:
                A list of tuples with the sub-file path and the datetime of it's
                last modification on the server, sorted oldest to newest.
            - If a list of files are provided:
                A dictionary where each key is the path and each value is
                a list of tuples with the sub-file path and the datetime of it's
                last modification on the server, sorted oldest to newest.
        """
        ...

    @overload
    def get_files_in_folder_in_date_order(
        self,
        path: Iterable[str | pathlib.Path],
        name_pattern: str | None = None,
        extensions: Iterable[str] | None = None,
        workspace_override: str | None = None
    ) -> dict[str, tuple[P4PathDateData, ...]]:
        ...

    def get_info(self) -> Any:
        """
        Display information about the current Helix Server application
        and the shared versioning service.

        More information here:
        https://www.perforce.com/manuals/cmdref/Content/CmdRef/p4_info.html#p4_info
        """
        ...

    @overload
    def get_latest(
        self,
        path: str | pathlib.Path,
        workspace_override: str | None = None
    ) -> bool | None:
        """
        Get latest on the given file(s).

        Arguments:
        ----------
            - `path`: The file path(s) to get latest on.
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

        Returns:
        --------
            - If a single file is provided:
                `True` if successfully got latest, `False` if not and `None` if
                file does note exist on the server.
            - If a list of files are provided:
                A dictionary where each key is the path and each value is
                `True` if successfully got latest, `False` if not and `None` if
                file does note exist on the server.
        """
        ...

    @overload
    def get_latest(
        self,
        path: Iterable[str | pathlib.Path],
        workspace_override: str | None = None
    ) -> dict[str, bool | None]:
        ...

    @overload
    def get_local_path(
        self,
        path: str | pathlib.Path,
        workspace_override: str | None = None
    ) -> str:
        """
        Get the local paths of the given file(s)

        Arguments:
        ----------
            - `path`: The depot file path(s) to get the local path(s) of
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

        Returns:
        --------
            - If a single file is provided:
                A string containing the local path.
            - If a list of files are provided:
                A dictionary where each key is the path and each value is
                a string containing the local path.
        """
        ...

    @overload
    def get_local_path(
        self,
        path: Iterable[str | pathlib.Path],
        workspace_override: str | None = None
    ) -> dict[str, str]:
        """
        Get the local paths of the given file(s)

        Arguments:
        ----------
            - `path`: The depot file path(s) to get the local path(s) of
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

        Returns:
        --------
            - If a single file is provided:
                A string containing the local path.
            - If a list of files are provided:
                A dictionary where each key is the path and each value is
                a string containing the local path.
        """
        ...

    @overload
    def get_newest_file_in_folder(
        self,
        path: str | pathlib.Path,
        name_pattern: str | None = None,
        extensions: Iterable[str] | None = None,
        workspace_override: str | None = None
    ) -> P4PathDateData | None:
        """
        Get the most recently modified file in the given folder(s).

        This is based on the last modified date and time on the server.

        Arguments:
        ----------
            - `path`: The directory path(s) to get the latest sub-file from.
            - `name_pattern` (optional): A specific name pattern used to filter
                the returned files by name. If `None`, no files are filtered.
                Defaults to `None`
            - `extensions` (optional): A list of file extensions used to filter
                the returned files by. If `None` no files are filtered.
                Defaults to `None`
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

        Returns:
        --------
            - If a single file is provided:
                `True` if successfully got latest, `False` if not.
            - If a list of files are provided:
                A dictionary where each key is the path and each value is
                `True` if successfully got latest, `False` if not.
        """
        ...

    @overload
    def get_newest_file_in_folder(
        self,
        path: Iterable[str | pathlib.Path],
        name_pattern: str | None = None,
        extensions: Iterable[str] | None = None,
        workspace_override: str | None = None
    ) -> dict[str, P4PathDateData | None]:
        ...


    @overload
    def get_path_info(
        self,
        path: str | pathlib.Path,
        workspace_override: str | None = None
    ) -> list[dict[str, str]]:
        """
        Get path info for the given path(s)

        For more information, see the perforce documentation:
        https://www.perforce.com/manuals/cmdref/Content/CmdRef/p4_where.html#p4_where

        Arguments:
        ----------
            - `path`: Path(s) to ge the info of.
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

        Returns:
        --------
            - If a single file is provided:
                A dictionary containing the path info.
            - If a list of files are provided:
                A dictionary where each key is the path and each value is
                a dictionary containing the path info.
        """
        ...

    @overload
    def get_path_info(
        self,
        path: Iterable[str | pathlib.Path],
        workspace_override: str | None = None
    ) -> list[dict[str, str]]:
        ...

    @overload
    def get_revision(
        self,
        path: Iterable[str | pathlib.Path],
        revision: Iterable[int] | int,
        workspace_override: str | None = None
    ) -> list[bool]:
        """
        Get the given revision(s) of the given file(s).

        Arguments:
        ----------
            - `path`: The file path(s) to get revisions of.
            - `revision`: The revision number to get. If a list of numbers is provided,
                `len(revision)` must match `len(path)` or will raise an `AttributeError`.
                If a single number is provided then the same revision number will be use
                for all files.
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

        Returns:
        --------
            - If a single file is provided:
                `True` if specified revision was successfully gotten , `False` if not.
            - If a list of files are provided:
                A dictionary where each key is the path and each value is
                `True` if specified revision was successfully gotten , `False` if not.
        """
        ...

    @overload
    def get_revision(
        self,
        path: str | pathlib.Path,
        revision: int,
        workspace_override: str | None = None
    ) -> bool:
        """ """
        ...

    def get_revision_history(
        self,
        path: Union[Iterable[str], Iterable[pathlib.Path], str, pathlib.Path], include_all: bool = ...
    ) -> Any:
        """# Not functional"""
        ...

    @overload
    def get_server_path(
        self,
        path: str | pathlib.Path,
        workspace_override: str | None = None
    ) -> str:
        """
        Get the server path(s) of the given file(s)

        Arguments:
        ----------
            - `path`: The depot file path(s) to get the server path(s) of
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

        Returns:
        --------
            - If a single file is provided:
                A string containing the server path.
            - If a list of files are provided:
                A dictionary where each key is the path and each value is
                a string containing the server path.
        """
        ...

    @overload
    def get_server_path(
        self,
        path: Iterable[str | pathlib.Path],
        workspace_override: str | None = None
    ) -> dict[str, str]:
        ...

    @overload
    def get_stat(
        self,
        path: str | pathlib.Path,
        args: Iterable[str] | None = None,
        workspace_override: str | None = None
    ) -> dict[str, str] | list[dict[str, str]]:
        """
        Run fstat on the given file(s).

        The standard fstat call will throw an exception if on
        of the files does not exist on the server.
        This function will not throw an exception, instead inserting
        an empty dictionary into the `result_stat[<local-path>]` value.

        This is more robust as knowledge of the path's existence on perforce
        does not need to be known before this or any wrapping function is
        called.

        Arguments:
        ----------
            - `path`: The file path(s) to get fstat for.
            - `args` (optional): List of extra arguments to include
                in the fstat command.
                Defaults to `None`
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

        Returns:
        --------
            - If a single file:
                A dictionary containing the fstat info.
            - If a list of files:
                A list of dictionaries containing the fstat info.
            - In the case of a file not existing on the server,
                an empty dict is returned instead.
        """
        ...

    @overload
    def get_stat(
        self,
        path: Iterable[str | pathlib.Path],
        args: Iterable[str] | None = None,
        workspace_override: str | None = None
    ) -> dict[str, dict[str, str] | list[dict[str, str]]]:
        """ """
        ...

    def get_streams(self) -> tuple[str]:
        """
        Get a list of all streams available to the current user and host.

        Arguments:
        ----------
            None

        Returns:
        --------
            - A tuple of streams.
        """
        ...

    def get_user_name(self) -> str:
        """
        Get the current perforce user name

        Arguments:
        ----------
            None

        Returns:
        --------
            - A string containing the current perforce user name.
        """
        ...

    @overload
    def get_version_info(
        self,
        path: str | pathlib.Path,
        workspace_override: str | None = None
    ) -> tuple[int | None, int | None]:
        """
        Get client and server versions for the given path(s).

        Arguments:
        ----------
            - `path`: The file path(s) to get the versions of.
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

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
    def get_version_info(
        self,
        path: Iterable[str | pathlib.Path],
        workspace_override: str | None = None
    ) -> list[tuple[int | None, int | None]]:
        ...

    def get_workspaces(self, stream: str | None = None) -> list[str]:

        """
        Get a list of all workspaces available to the current user and host.

        Arguments:
        ----------
            `stream` (optional): If defined, get all workspaces on the given
                stream only.
                Defaults to `None`

        Returns:
        --------
            - A list of workspaces.
        """
        ...

    @overload
    def is_checked_out_by_user(
        self,
        path: str | pathlib.Path,
        user_name: tuple[str] | str | None = None,
        workspace_override: str | None = None
    ) -> bool:
        """
        Query if the given path(s) are checked out by the given user.

        Arguments:
        ----------
            - `path`: The file path(s) to get fstat for.
            - `user_name` (optional): blah blah
                Defaults to `None`
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

        Returns:
        --------
            - If a single file:
                A dictionary containing the fstat info.
            - If a list of files:
                A list of dictionaries containing the fstat info.
            - In the case of a file not existing on the server,
                an empty dict is returned instead.
        """
        ...

    @overload
    def is_checked_out_by_user(
        self,
        path: Iterable[str | pathlib.Path],
        user_name: tuple[str] | str | None = None,
    ) -> dict[str, bool]:
        """ """
        ...

    @overload
    def is_checked_out(
        self,
        path: Iterable[str | pathlib.Path],
        workspace_override: str | None = None
    ) -> dict[str, bool]:
        """
        Query if the given path(s) are checked out.

        Arguments:
        ----------
            - `path`: The path(s) to query the checkout status of.
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

        Returns:
        --------
            - If a single file is provided:
                `True` if file is checked out, `False` if not and `None`
                if the file is not on the server.
            - If a list of files are provided:
                A dictionary where each key is the path and each value is
                `True` if file is checked out, `False` if not and `None`
                if the file is not on the server.
            - If a path is a directory, will query all sub-files,
                returning `True` if all are checked out and `False`
                if at least one file is not checked out.
        """
        ...

    @overload
    def is_checked_out(
        self,
        path: str |pathlib.Path,
        workspace_override: str | None = None
    ) -> bool:
        ...

    @overload
    def is_latest(
        self,
        path: str | pathlib.Path,
        workspace_override: str | None = None
    ) -> bool | None:

        """
        Query if the given path(s) are the latest version locally.

        Arguments:
        ----------
            - `path`: The path(s) to query the status of.
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully. Defaults to `None`

        Returns:
        --------
            - If a single file is provided:
                `True` if file is latest, `False` if not and `None`
                if the file is not on the server.
            - If a list of files are provided:
                A dictionary where each key is the path and each value is
                `True` if file is latest, `False` if not and `None`
                if the file is not on the server.
            - If a path is a directory, will query all sub-files,
                returning `True` if all are latest and `False`
                if at least one file is not latest.
        """
        ...

    @overload
    def is_latest(
        self,
        path: Iterable[str | pathlib.Path],
        workspace_override: str | None = None
    ) -> dict[str, bool | None]:
        ...

    def is_stream_valid(self, stream: str) -> bool:
        """
        Query if the given stream is valid for this user and host.

        Arguments:
        ----------
            `stream`: The name of the stream to query.

        Returns:
        --------
            - `True` if valid, `False` if not.
        """
        ...

    @overload
    def move(
        self,
        path: str | pathlib.Path,
        target_path: str | pathlib.Path,
        change_description: str | None = None,
        get_latest: bool = True,
        workspace_override: str | None = None
    ) -> bool:
        """
        Move the given path(s).

        Arguments:
        ----------
            - `path`: The source path(s) to move.
            - `target_path`: The target path(s) to move to.
            - `change_description` (optional): If provided, the description of the
                change list to add the moved file(s) to. If None, will add them
                to the default change list. Defaults to `None`
            - `get_latest` (optional): If `True`, sync `path` and `target_path` before
                attempting move command. If the sync fails, then the move will fail too.
                Defaults to `True`
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

        Returns:
        --------
            If a single file is provided:
                `True` if successfully moved, `False` if not.
            If a list of files are provided:
                A dictionary where each key is the path and each value is
                `True` if successfully moved, `False` if not.
        """
        ...

    @overload
    def move(
        self,
        path: Iterable[str | pathlib.Path],
        target_path: Iterable[str | pathlib.Path],
        change_description: str | None = None,
        get_latest: bool = True,
        workspace_override: str | None = None
    ) -> dict[str, bool]:
        ...

    @overload
    def revert(
        self,
        path: str | pathlib.Path,
        workspace_override: str | None = None
    ) -> bool:
        """
        Revert the given path(s).

        Arguments:
        ----------
            - `path`: The source path(s) to revert.
            - `workspace_override` (optional): If provided, uses the specific workspace
                to first run the command under. If `None`, will use the current workspace
                define by the local perforce settings. If the function fails, will
                iterate over all other workspaces, running the function to see
                if it will run successfully.
                Defaults to `None`

        Returns:
        --------
            If a single file is provided:
                `True` if successfully reverted, `False` if not.
            If a list of files are provided:
                A dictionary where each key is the path and each value is
                `True` if successfully reverted, `False` if not.
        """
        ...

    @overload
    def revert(
        self,
        path: Iterable[str | pathlib.Path],
        workspace_override: str | None = None
    ) -> dict[str, bool]:
        """ """
        ...

    def test_connection(self) -> bool:
        """
        Test if connected to perforce server.
        """


is_offline: bool = ...
""" Flag denoting if the perforce server is offline.
"""


exceptions: p4_errors.P4Exceptions = ...
""" Enum holding all exception types
"""


def _get_connection_manager() -> P4ConnectionManager:
    """
    Get the P4ConnectionManager singleton instance
    """


@overload
def add(
    path: str | pathlib.Path,
    change_description: str | None = None,
    workspace_override: str | None = None
) -> bool:
    """
    Add the given path(s) if they do not exists on the server already.

    Arguments:
    ----------
        - `path`: The path(s) to add
        - `change_description` (optional): If provided, the description of the
            change list to add the added file(s) to. If None, will add them
            to the default change list. Defaults to `None`
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        If a single file is provided:
            `True` if successfully added, `False` if not.
        If a list of files are provided:
            A dictionary where each key is the path and each value is
            `True` if successfully added, `False` if not.
    """
    ...


@overload
def add(
    path: Iterable[str | pathlib.Path],
    change_description: str | None = None,
    workspace_override: str | None = None
) -> dict[str, bool]:
    """
    Add the given file if it does not exists on the server already.
    """
    ...


def add_to_change_list(
    path: str | pathlib.Path | Iterable[str | pathlib.Path],
    description: str,
    workspace_override: str | None = None
) -> bool:
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
def checkout(
    path: str | pathlib.Path,
    change_description: str | None = None,
    workspace_override: str | None = None
) -> bool:
    """
    Checkout the given path(s) if they exist on the server.

    Arguments:
    ----------
        - `path`: The path(s) to checkout
        - `change_description` (optional): If provided, the description of the
            change list to add the checked out file(s) to. If None, will add them
            to the default change list. Defaults to `None`
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        If a single file is provided:
            `True` if successfully checked out, `False` if not.
        If a list of files are provided:
            A dictionary where each key is the path and each value is
            `True` if successfully checked out, `False` if not.
    """
    ...


@overload
def checkout(
    path: Iterable[str | pathlib.Path],
    change_description: str | None = None,
    workspace_override: str | None = None
) -> dict[str, bool]:
    ...


def create_change_list(
    description: str,
    files: Iterable[str | pathlib.Path] | None = None,
    workspace_override: str | None = None
) -> bool:
    """
    Create a change list with the given description and optional files.

    Arguments:
    ----------
        - `description`: The change list description. If a change list
            already exists with this description, it will be used instead
            of creating a new one.
        - `files` (optional): Defines a list of files to add to the change list.
            Defaults to None
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        `True` on success, `False` on Failure.
    """
    ...


def create_workspace(name: str, root: str, stream: str) -> Any:
    """# Not functional"""
    ...


@overload
def delete(
    path: str | pathlib.Path,
    change_description: str | None = None,
    workspace_override: str | None = None
) -> bool:
    """
    Delete the given file(s) if they exists on the server.

    Note that the files will be deleted locally, but not from
    the server until their respective change list is submitted!

    Arguments:
    ----------
        - `path`: The file path(s) to delete from the server.
        - `change_description` (optional): If provided, the description of the
            change list to add the deleted file(s) to. If None, will add them
            to the default change list. Defaults to `None`
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        - If a single file is provided:
            `True` if successfully deleted, `False` if not.
        - If a list of files are provided:
            A dictionary where each key is the path and each value is
            `True` if successfully deleted, `False` if not.
    """
    ...


@overload
def delete(
    path: Iterable[str | pathlib.Path],
    change_description: str | None = None,
    workspace_override: str | None = None
) -> list[bool]:
    ...


def delete_change_list(
    description: str,
    force: bool = False,
    workspace_override: str = "",
) -> bool:
    """
    Delete a change list based on it's description.

    Arguments:
    ----------
        - `description`: The description of the change list to delete.
        - `force` (optional): If `True` - remove any files in the change list to the
            default change list before deleting. The default behaviour of P4 is to
            fail to delete a change list if it contains files. Defaults to `False`
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        `True` if successfully deleted, `False` if not.
    """
    ...


@overload
def checked_out_by(
    path: str | pathlib.Path,
    other_users_only: bool = False,
    fstat_args: Iterable[str] | None = None,
    workspace_override: str | None = None
) -> list[str] | None:
    """
    Get a list of users that the given file(s) are checked out by.

    Arguments:
    ----------
        - `path`: The path(s) to query.
        - `other_users_only` (optional): If `True`, will not include current user
            in list of users with file checked out, if the file is checked out
            by the current user. Defaults to `True`
        - `fstat_args` (optional): If provided, a list of arguments to use
            when running the fstat command to run the checked out query with.
            Refer to the perforce docs for more information:
            https://www.perforce.com/manuals/cmdref/Content/CmdRef/p4_fstat.html
            Defaults to `None`
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        If a single file is provided:
            A list of users who have the file checked out or
            `None` if the file is not checked out.
        If a list of files are provided:
            A dictionary where each key is the path and each value is
            a list of users who have the given file checked out or
            `None` if the given file is not checked out.
    """
    ...


@overload
def checked_out_by(
    path: Iterable[str | pathlib.Path],
    other_users_only: bool = False,
    fstat_args: Iterable[str] | None = None,
    workspace_override: str | None = None
) -> list[list[str] | None]:
    ...


@overload
def exists_on_server(
    path: str | pathlib.Path,
    workspace_override: str | None = None
) -> bool:
    """
    Query if the given path(s) exist on the server.

    Arguments:
    ----------
        - `path`: The path(s) to query.
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        If a single file is provided:
            `True` if the path exists, `False` if not.
        If a list of files are provided:
            A dictionary where each key is the path and each value is
            `True` if the path exists, `False` if not.
    """
    ...


@overload
def exists_on_server(
    path: Iterable[str | pathlib.Path],
    workspace_override: str | None = None
) -> dict[str, bool]:
    ...


@overload
def get_attribute(
    path: str | pathlib.Path,
    name: str,
    default: Any = None,
    raise_error:bool = False
) -> Any:
    """
    Get the attribute from the given file(s).

    Arguments:
    ----------
        - `path`: The file path(s) to get the attribute on.
        - `name`: The name of the attribute to get.
        - `default` (optional): The default value to return if the file(s) do not
            have an attribute with the given name. Requires `raise_error` to be `False`
            Defaults to `None`
        - `raise_error` (optional): If `True` will raise `P4AttributeError` during the
            function call if a file does not have the attribute. This is immediate.
            If `False` will print the error but allow the function to complete, returning
            the object set in the `default` argument.
            Defaults to `False`
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Raises:
    -------
        If `raise_error` is True, the function will exit upon the first file without
        the given attribute, raising `P4AttributeError`

    Returns:
    --------
        - If a single file is provided:
            The value of the attribute if it exists. `default` value if it does not.
        - If a list of files are provided:
            A dictionary where each key is the path and each value is
            The value of the attribute if it exists. `default` value if it does not.
    """
    ...


@overload
def get_attribute(
    path: Iterable[str | pathlib.Path],
    name: str,
    default: Any = None,
    raise_error:bool = False,
    workspace_override: str | None = None
) -> dict[str, Any]:
    ...


def get_client_root(workspace_override: str | None = None) -> str:
    """
    Get the local path root for the current workspace.

    Arguments:
    ----------
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully. Defaults to `None`

    Returns:
    --------
        A string of the local path root.
    """
    ...


@overload
def get_current_client_revision(
    path: str | pathlib.Path,
    workspace_override: str | None = None
) -> int | None:
    """
    Get the current client revision numbers for the given path(s)

    Arguments:
    ----------
        - `path`: The file path(s) to get the client revision of.
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

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
def get_current_client_revision(
    path: Iterable[str | pathlib.Path], workspace_override: str | None = None
) -> dict[str, int | None]:
    ...


@overload
def get_current_revision_info(
    path: str | pathlib.Path,
    workspace_override: str | None = None
) -> tuple[int, int] | tuple[int, Literal[0]] | tuple[None, None]:
    """
    Get the current source and client revision numbers for the given path(s)

    Arguments:
    ----------
        - `path`: The file path(s) to get the client revision of.
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        - If a single file is provided:
            A tuple containing the server and local version numbers.
            Returns a tuple`[<server_index>, 0]` if the file does not exist locally
            or `tuple[None, None]` if the file does not exist on the server.
        - If a list of files are provided:
            A dictionary where each key is the path and each value is
            a tuple containing the server and local version numbers.
            Returns a tuple`[<server_index>, 0]` if the file does not exist locally
            or `tuple[None, None]` if the file does not exist on the server.
    """
    ...


@overload
def get_current_revision_info(
    path: Iterable[str | pathlib.Path],
    workspace_override: str | None = None
) -> dict[str, tuple[int, int] | tuple[int, Literal[0]] | tuple[None, None]]:
    ...


@overload
def get_current_server_revision(
    path: str | pathlib.Path,
    workspace_override: str | None = None
) -> int | None:
    """
    Get the current server revision numbers for the given path(s)

    Arguments:
    ----------
        - `path`: The file path(s) to get the server revision of.
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

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
def get_current_server_revision(
    path: Iterable[str | pathlib.Path],
    workspace_override: str | None = None
) -> dict[str, int | None]:
    ...


def get_existing_change_list(
    description: str,
    workspace_override: str | None = None
) -> dict[str, Any] | None:
    """
    Get and existing changelist with the given description.

    Arguments:
    ----------
        - `description`: The change list description.
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        - A dictionary describing the existing change list.
    """
    ...


@overload
def get_files(
    path: str | pathlib.Path,
    extension: str | None = None,
    include_all: bool = False,
    query_sub_folders: bool = False,
    workspace_override: str | None = None
) -> tuple[pathlib.Path]:
    """
    Get a list of files in the given folder(s).

    Arguments:
    ----------
        - `path`: The directory path(s) to get the sub-files of.
        - `extension` (optional): If provided, will filter the result by the extension type.
            Defaults  to `None`
        - `include_all` (optional): If `True`, will include deleted, purged, and archived files.
            If `False` only include files available for syncing or integration.
            Defaults  to `False`
        - `query_sub_folders` (optional): If `True, will get all sub-files of sub-folders.
            Defaults to `True`
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        - If a single file is provided:
            A tuple with the sub-files of the given folder.
        - If a list of files are provided:
            A dictionary where each key is the path and each value is
            a tuple with the sub-files of the given folder.
    """
    ...


@overload
def get_files(
    path: Iterable[str | pathlib.Path],
    extension: str | None = None,
    include_all: bool = False,
    query_sub_folders: bool = False,
    workspace_override: str | None = None
) -> dict[str, tuple[pathlib.Path]]:
    ...


@overload
def get_files_in_folder_in_date_order(
    path: str | pathlib.Path,
    name_pattern: str | None = None,
    extensions: Iterable[str] | None = None,
    workspace_override: str | None = None
) -> tuple[P4PathDateData, ...] | None:
    """
    Get a list of files in the given folder(s) in date order,
    oldest to newest.

    Arguments:
    ----------
        - `path`: The directory path(s) to get the sub-files of.
        - `name_pattern` (optional): A specific name pattern used to filter
            the returned files by name. If `None`, no files are filtered.
            Defaults to `None`
        - `extensions` (optional): A list of file extensions used to filter
            the returned files by. If `None` no files are filtered.
            Defaults to `None`
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        - If a single file is provided:
            A list of tuples with the sub-file path and the datetime of it's
            last modification on the server, sorted oldest to newest.
        - If a list of files are provided:
            A dictionary where each key is the path and each value is
            a list of tuples with the sub-file path and the datetime of it's
            last modification on the server, sorted oldest to newest.
    """
    ...


@overload
def get_files_in_folder_in_date_order(
    path: Iterable[str | pathlib.Path],
    name_pattern: str | None = None,
    extensions: Iterable[str] | None = None,
    workspace_override: str | None = None
) -> dict[str, tuple[P4PathDateData, ...]] | None:
    ...


def get_info() -> Any:
    """
    Display information about the current Helix Server application
    and the shared versioning service.

    More information here:
    https://www.perforce.com/manuals/cmdref/Content/CmdRef/p4_info.html#p4_info
    """
    ...


@overload
def get_latest(
    path: str | pathlib.Path,
    workspace_override: str | None = None
) -> bool | None:
    """
    Get latest on the given file(s).

    Arguments:
    ----------
        - `path`: The file path(s) to get latest on.
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        - If a single file is provided:
            `True` if successfully got latest, `False` if not and `None` if
            file does note exist on the server.
        - If a list of files are provided:
            A dictionary where each key is the path and each value is
            `True` if successfully got latest, `False` if not and `None` if
            file does note exist on the server.
    """
    ...


@overload
def get_latest(
    path: Iterable[str | pathlib.Path],
    workspace_override: str | None = None
) -> dict[str, bool | None]:
    ...


@overload
def get_local_path(
    path: str | pathlib.Path,
    workspace_override: str | None = None
) -> str:
    """
    Get the local paths of the given file(s)

    Arguments:
    ----------
        - `path`: The depot file path(s) to get the local path(s) of
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        - If a single file is provided:
            A string containing the local path.
        - If a list of files are provided:
            A dictionary where each key is the path and each value is
            a string containing the local path.
    """
    ...


@overload
def get_local_path(
    path: Iterable[str | pathlib.Path],
    workspace_override: str | None = None
) -> dict[str, str]:
    """
    Get the local paths of the given file(s)

    Arguments:
    ----------
        - `path`: The depot file path(s) to get the local path(s) of
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        - If a single file is provided:
            A string containing the local path.
        - If a list of files are provided:
            A dictionary where each key is the path and each value is
            a string containing the local path.
    """
    ...


@overload
def get_newest_file_in_folder(
    path: str | pathlib.Path,
    name_pattern: str | None = None,
    extensions: Iterable[str] | None = None,
    workspace_override: str | None = None
) -> P4PathDateData | None:
    """
    Get the most recently modified file in the given folder(s).

    This is based on the last modified date and time on the server.

    Arguments:
    ----------
        - `path`: The directory path(s) to get the latest sub-file from.
        - `name_pattern` (optional): A specific name pattern used to filter
            the returned files by name. If `None`, no files are filtered.
            Defaults to `None`
        - `extensions` (optional): A list of file extensions used to filter
            the returned files by. If `None` no files are filtered.
            Defaults to `None`
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        - If a single file is provided:
            `True` if successfully got latest, `False` if not.
        - If a list of files are provided:
            A dictionary where each key is the path and each value is
            `True` if successfully got latest, `False` if not.
    """
    ...


@overload
def get_newest_file_in_folder(
    path: Iterable[str | pathlib.Path],
    name_pattern: str | None = None,
    extensions: Iterable[str] | None = None,
    workspace_override: str | None = None
) -> dict[str, P4PathDateData | None]:
    ...


@overload
def get_path_info(
    path: str | pathlib.Path,
    workspace_override: str | None = None
) -> list[dict[str, str]]:
    """
    Get path info for the given path(s)

    For more information, see the perforce documentation:
    https://www.perforce.com/manuals/cmdref/Content/CmdRef/p4_where.html#p4_where

    Arguments:
    ----------
        - `path`: Path(s) to ge the info of.
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        - If a single file is provided:
            A dictionary containing the path info.
        - If a list of files are provided:
            A dictionary where each key is the path and each value is
            a dictionary containing the path info.
    """
    ...


@overload
def get_path_info(
    path: Iterable[str | pathlib.Path],
    workspace_override: str | None = None
) -> list[dict[str, str]]:
    ...


@overload
def get_revision(
    path: Iterable[str | pathlib.Path],
    revision: Iterable[int] | int,
    workspace_override: str | None = None
) -> list[bool]:
    """
    Get the given revision(s) of the given file(s).

    Arguments:
    ----------
        - `path`: The file path(s) to get revisions of.
        - `revision`: The revision number to get. If a list of numbers is provided,
            `len(revision)` must match `len(path)` or will raise an `AttributeError`.
            If a single number is provided then the same revision number will be use
            for all files.
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        - If a single file is provided:
            `True` if specified revision was successfully gotten , `False` if not.
        - If a list of files are provided:
            A dictionary where each key is the path and each value is
            `True` if specified revision was successfully gotten , `False` if not.
    """
    ...


@overload
def get_revision(
    path: str | pathlib.Path,
    revision: int,
    workspace_override: str | None = None
) -> bool:
    """ """
    ...


def get_revision_history(
    path: Union[Iterable[str], Iterable[pathlib.Path], str, pathlib.Path], include_all: bool = ...
) -> Any:
    """ """
    ...


@overload
def get_server_path(
    path: str | pathlib.Path,
    workspace_override: str | None = None
) -> str:
    """
    Get the server path(s) of the given file(s)

    Arguments:
    ----------
        - `path`: The depot file path(s) to get the server path(s) of
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        - If a single file is provided:
            A string containing the server path.
        - If a list of files are provided:
            A dictionary where each key is the path and each value is
            a string containing the server path.
    """
    ...


@overload
def get_server_path(
    path: Iterable[str | pathlib.Path],
    workspace_override: str | None = None
) -> dict[str, str]:
    ...


@overload
def get_stat(
    path: str | pathlib.Path,
    args: Iterable[str] | None = None,
    workspace_override: str | None = None
) -> dict[str, str] | list[dict[str, str]]:
    """
    Run fstat on the given file(s).

    The standard fstat call will throw an exception if on
    of the files does not exist on the server.
    This function will not throw an exception, instead inserting
    an empty dictionary into the `result_stat[<local-path>]` value.

    This is more robust as knowledge of the path's existence on perforce
    does not need to be known before this or any wrapping function is
    called.

    Arguments:
    ----------
        - `path`: The file path(s) to get fstat for.
        - `args` (optional): List of extra arguments to include
            in the fstat command.
            Defaults to `None`
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        - If a single file:
            A dictionary containing the fstat info.
        - If a list of files:
            A list of dictionaries containing the fstat info.
        - In the case of a file not existing on the server,
            an empty dict is returned instead.
    """
    ...


@overload
def get_stat(
    path: Iterable[str | pathlib.Path],
    args: Iterable[str] | None = None,
    workspace_override: str | None = None
) -> dict[str, dict[str, str] | list[dict[str, str]]]:
    """ """
    ...


def get_streams() -> tuple[str]:
    """
    Get a list of all streams available to the current user and host.

    Arguments:
    ----------
        None

    Returns:
    --------
        - A tuple of streams.
    """
    ...


def get_user_name() -> str:
    """
    Get the current perforce user name

    Arguments:
    ----------
        None

    Returns:
    --------
        - A string containing the current perforce user name.
    """
    ...


@overload
def get_version_info(
    path: str | pathlib.Path,
    workspace_override: str | None = None
) -> tuple[int | None, int | None]:
    """
    Get client and server versions for the given path(s).

    Arguments:
    ----------
        - `path`: The file path(s) to get the versions of.
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

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
def get_version_info(
    path: Iterable[str | pathlib.Path],
    workspace_override: str | None = None
) -> list[tuple[int | None, int | None]]:
    ...


def get_workspaces(stream: str | None = None) -> list[str]:
    """
    Get a list of all workspaces available to the current user and host.

    Arguments:
    ----------
        `stream` (optional): If defined, get all workspaces on the given
            stream only.
            Defaults to `None`

    Returns:
    --------
        - A list of workspaces.
    """
    ...


@overload
def is_checked_out_by_user(
    path: str | pathlib.Path,
    user_name: tuple[str] | str | None = None,
    workspace_override: str | None = None
) -> bool:
    """
    Query if the given path(s) are checked out by the given user.

    Arguments:
    ----------
        - `path`: The file path(s) to get fstat for.
        - `user_name` (optional): blah blah
            Defaults to `None`
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        - If a single file:
            A dictionary containing the fstat info.
        - If a list of files:
            A list of dictionaries containing the fstat info.
        - In the case of a file not existing on the server,
            an empty dict is returned instead.
    """
    ...


@overload
def is_checked_out_by_user(
    path: Iterable[str | pathlib.Path],
    user_name: tuple[str] | str | None = None,
) -> dict[str, bool]:
    """ """
    ...


@overload
def is_checked_out(path: Iterable[str | pathlib.Path], workspace_override: str | None = None) -> dict[str, bool]:
    """
    Query if the given path(s) are checked out.

    Arguments:
    ----------
        - `path`: The path(s) to query the checkout status of.
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        - If a single file is provided:
            `True` if file is checked out, `False` if not and `None`
            if the file is not on the server.
        - If a list of files are provided:
            A dictionary where each key is the path and each value is
            `True` if file is checked out, `False` if not and `None`
            if the file is not on the server.
        - If a path is a directory, will query all sub-files,
            returning `True` if all are checked out and `False`
            if at least one file is not checked out.
    """
    ...


@overload
def is_checked_out(path: str |pathlib.Path, workspace_override: str | None = None) -> bool:
    ...


@overload
def is_latest(
    path: str | pathlib.Path,
    workspace_override: str | None = None
) -> bool | None:

    """
    Query if the given path(s) are the latest version locally.

    Arguments:
    ----------
        - `path`: The path(s) to query the status of.
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully. Defaults to `None`

    Returns:
    --------
        - If a single file is provided:
            `True` if file is latest, `False` if not and `None`
            if the file is not on the server.
        - If a list of files are provided:
            A dictionary where each key is the path and each value is
            `True` if file is latest, `False` if not and `None`
            if the file is not on the server.
        - If a path is a directory, will query all sub-files,
            returning `True` if all are latest and `False`
            if at least one file is not latest.
    """
    ...


@overload
def is_latest(
    path: Iterable[str | pathlib.Path],
    workspace_override: str | None = None
) -> dict[str, bool | None]:
    ...


def is_stream_valid(stream: str) -> bool:
    """
    Query if the given stream is valid for this user and host.

    Arguments:
    ----------
        `stream`: The name of the stream to query.

    Returns:
    --------
        - `True` if valid, `False` if not.
    """
    ...


@overload
def move(
    path: str | pathlib.Path,
    target_path: str | pathlib.Path,
    change_description: str | None = None,
    get_latest: bool = True,
    workspace_override: str | None = None
) -> bool | None:
    """
    Move the given path(s).

    Arguments:
    ----------
        - `path`: The source path(s) to move.
        - `target_path`: The target path(s) to move to.
        - `change_description` (optional): If provided, the description of the
            change list to add the moved file(s) to. If None, will add them
            to the default change list. Defaults to `None`
        - `get_latest` (optional): If `True`, sync `path` and `target_path` before
            attempting move command. If the sync fails, then the move will fail too.
            Defaults to `True`
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        If a single file is provided:
            `True` if successfully moved, `False` if not.
        If a list of files are provided:
            A dictionary where each key is the path and each value is
            `True` if successfully moved, `False` if not.
    """
    ...


@overload
def move(
    path: Iterable[str | pathlib.Path],
    target_path: Iterable[str | pathlib.Path],
    change_description: str | None = None,
    get_latest: bool = True,
    workspace_override: str | None = None
) -> dict[str, bool | None]:
    ...


@overload
def revert(
    path: str | pathlib.Path,
    workspace_override: str | None = None
) -> bool:
    """
    Revert the given path(s).

    Arguments:
    ----------
        - `path`: The source path(s) to revert.
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        If a single file is provided:
            `True` if successfully reverted, `False` if not.
        If a list of files are provided:
            A dictionary where each key is the path and each value is
            `True` if successfully reverted, `False` if not.
    """
    ...


@overload
def revert(
    path: Iterable[str | pathlib.Path],
    workspace_override: str | None = None
) -> dict[str, bool]:
    """ """
    ...


def run_command(cmd: str, *args, **kwargs) -> Any:
    """ """
    ...


@overload
def set_attribute(
    path: str | pathlib.Path,
    name: str,
    value: Any,
    workspace_override: str | None = None
) -> bool:
    """
    Set the given attribute to the given value on the given file(s).

    Arguments:
    ----------
        - `path`: The file path(s) to set the attribute on.
        - `name`: The name of the attribute to set.
        - `value`: The value of the attribute to set.
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        - If a single file is provided:
            `True` if successful, `False` if not.
        - If a list of files are provided:
            A dictionary where each key is the path and each value is
            `True` if successful, `False` if not.
    """
    ...


@overload
def set_attribute(
    path: Iterable[str | pathlib.Path],
    name: str,
    value: Any,
    workspace_override: str | None = None
) -> dict[str, bool]:
    ...


def submit_change_list(name: str) -> int | None:
    """ """
    ...


@overload
def sync(path: str | pathlib.Path, workspace_override: str | None = None) -> bool:
    """
    Synonym for get_latest
    """
    ...


@overload
def sync(path: Iterable[str | pathlib.Path], workspace_override: str | None = None) -> dict[str, bool]:
    ...


def test_connection() -> bool:
    """
    Test if connected to perforce server.
    """


@overload
def unsync(path: str | pathlib.Path, workspace_override: str | None = None) -> bool:
    """
    Unsync the given file(s), removing them locally.

    This is different from just deleting locally which leaves perforce out
    of sync with the state of the local file, thinking it is on the last
    version synced to, or deleting on perforce which removes the file both
    locally and from the server.
    This removes the file(s) maintaining their state in perforce so they
    can be synced again at a later stage.

    Arguments:
    ----------
        - `path`: The file path(s) to unsyc.
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        - If a single file is provided:
            `True` if successfully unsyced, `False` if not.
        - If a list of files are provided:
            A dictionary where each key is the path and each value is
            `True` if successfully unsyced, `False` if not.
    """
    ...


@overload
def unsync(path: Iterable[str | pathlib.Path], workspace_override: str | None = None) -> dict[str, bool]:
    ...


def update_change_list_description(
    old_description: str, new_description: str, workspace_override: str | None = None
) -> bool:
    """
    Change the description of the change list matching the old description to the new one.

    Arguments:
    ----------
        - `old_description`: The old description, used to identify the
            change list.
        - `new_description`: The new description, to update the change
            list description to.
        - `workspace_override` (optional): If provided, uses the specific workspace
            to first run the command under. If `None`, will use the current workspace
            define by the local perforce settings. If the function fails, will
            iterate over all other workspaces, running the function to see
            if it will run successfully.
            Defaults to `None`

    Returns:
    --------
        - `True` if successful, `False` if not.
    """
    ...


@contextmanager
def workspace_as(workspace: str) -> Iterator[None]:
    """
    Context manager that connects to if not already connected p4,
    yielding the instance of p4 and closing the connection when done.
    """
    ...
