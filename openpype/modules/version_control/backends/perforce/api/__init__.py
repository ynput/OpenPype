"""
An easier, more pythonic inteface for working with P4, built on P4Python.
    Objects, methods and functions in this module handle connection
    and errors automatically, managing the verbose approach required
    in P4Python.
"""
from __future__ import annotations

import collections.abc as col_abc
import dataclasses
import datetime
import enum
import functools
import inspect
import pathlib
import Qt.QtCore as QtCore  # type: ignore
import socket
import sys
import threading
import typing

from . import p4_errors
from . import p4_offline
from ..vendor import P4

from contextlib import contextmanager
from functools import lru_cache
from types import MethodType

_typing = False
if _typing:
    from typing import Any
    from typing import Callable
    from typing import Generator
    from typing import Iterable
    from typing import Iterator
    from typing import Optional
    from typing import Sequence
    from typing import Union
    from typing_extensions import Literal

    P4PathType = Union[Iterable[str], Iterable[pathlib.Path], str, pathlib.Path]  # type: ignore
    T_PthStrLst = Union[list[str], tuple[str]]  # type: ignore
    P4ArgsType = Optional[Iterable[str]]  # type: ignore
    P4ReturnType = list[dict[str, str]]  # type: ignore
    P4ReturnWithNoneType = list[Optional[dict[str, str]]]  # type: ignore
    P4ReturnBoolType = Optional[Union[bool, list[bool]]]  # type: ignore

    T_Result = Union["Sequence[dict[str, str]]", "Iterable[dict[str, str]]", "Sequence[str]"]
    T_Keys = Union["str", "Sequence[str]"]
    T_Actions = Union["str", "Sequence[str]"]
    T_NoneKeys = Union["str", "Sequence[str]", None]
    T_NoneActions = Union["str", "Sequence[str]", None]

T_StrTuple = typing.NewType("T_StrTuple", "tuple[str]")


def make_tuple_if_not(value: Any) -> tuple[Any]:
    import openpype.lib
    return openpype.lib.make_tuple_if_not(value)


class E_RunOutput(enum.Enum):
    success = 0
    fail = 1


class P4ProgressSignaller(QtCore.QObject):
    started = QtCore.Signal(str, int)
    total_set = QtCore.Signal(int)
    updated = QtCore.Signal(int)
    completed = QtCore.Signal(str, int)


class P4ProgressHandler(P4.Progress):
    TYPES = ["Unknown", "Submit", "Sync", "Clone"]

    def __init__(
        self,
        started_fn: Callable[[str, int], None] | None = None,
        total_set_fn: Callable[[int], None] | None = None,
        updated_fn: Callable[[int], None] | None = None,
        completed_fn: Callable[[str, int], None] | None = None,
    ):
        super().__init__()

        self._signaller = None
        self._current_file = ""

        signaller = self.signaller
        if signaller:
            signaller.started.connect(started_fn) if started_fn else None
            signaller.total_set.connect(total_set_fn) if total_set_fn else None
            signaller.updated.connect(updated_fn) if updated_fn else None
            signaller.completed.connect(completed_fn) if completed_fn else None

    @property
    def signaller(self) -> P4ProgressSignaller:
        if self._signaller is None:
            self._signaller = self._get_signaller()
        return self._signaller

    def init(self, type):
        super().init(type)

    def setDescription(self, description: str, units: int):
        super().setDescription(description, units)
        self._current_file = description
        self.signaller.started.emit(description, units)

    def setTotal(self, total: int):
        super().setTotal(total)
        self.signaller.total_set.emit(total)

    def update(self, position: int):
        super().update(position)
        self.signaller.updated.emit(position)

    def done(self, fail: int):
        super().done(fail)
        self.signaller.completed.emit(self._current_file, fail)

    def _get_signaller(self) -> P4ProgressSignaller:
        return P4ProgressSignaller()


class P4ConnectionManagerSignaller(QtCore.QObject):
    connected = QtCore.Signal()
    disconnected = QtCore.Signal()


@dataclasses.dataclass(frozen=False)
class P4PathDateData:
    path: pathlib.Path | None = None
    date: datetime.datetime | None = None

    def set_data(self, path: pathlib.Path | None, date: datetime.datetime | None):
        self.path = path
        self.date = date


class P4ConnectionManager:
    """
    This class is the core of this module.

    It manages the connection and error handling
    when sending commands to p4 via P4Python.

    It does this by providing a number of convenience
    mechanisms to reduce boiler plate code.
    The main mechanism is the handling of methods
    which require a p4 connection.
    Any attribute that both has `_connect_` as a prefix
    and is a method, will lazily wrap said method with
    `__run_connect__` and remove the `_connect_` prefix.

    For example: `_connect_sync` will be accessed with `sync`.

    This offers multiple benefits:

    - core methods are marked as private.
    - wrapping of methods is handled lazily, thus is performant.
    - reduced verbosity of calling core method names.

    The `__run_connect__` wrapper works in conjunction with the
    `__connect__` context manager to automatically manage the
    p4.connect and p4.disconnect functionality.
    This is especially useful for nested `_connect_`
    method calls, as P4Python throws an exception if
    `p4.connect()` is called when an connection is already
    active.

    # *** Any method that requires a connection to p4,
    # must be declared with the prefix: `_connect_` ***

    The `__run_connect__` wrapper will also handle workspaces by
    attempting to run the given function in each workspace, returning
    as soon as the function runs successfully.
    The first workspace used will initially be the current workspace
    as defined by `p4.client`, and then it will be updated to
    the last workspace that a function was successfully run on.
    This should mean in most cases the function will only need to
    run the first time as most users pcs should be setup to have
    `p4.client` be their standard workspace, BUT if it fails, then
    the function will be run on all the other workspaces until it
    either succeeds or there are no workspaces left.
    """

    # Magic Methods:
    def __init__(
        self,
        use_progress_hander: bool = False,
        started_fn: Callable[[str, int], None] | None = None,
        total_set_fn: Callable[[int], None] | None = None,
        updated_fn: Callable[[int], None] | None = None,
        completed_fn: Callable[[str, int], None] | None = None
    ):

        super().__init__()

        self._p4 = None
        self._connection_depth: int = 0
        self._host_name: str = ""

        self._is_offline = False
        self._retry_p4_connection = False
        self._offline_manager = None

        self._break_run_loop: bool = False
        self._run_successfully: bool = False
        self.result: Any = None

        self._attribute_errors: set[str] = set()
        self._path_existence_errors: set[str] = set()
        self.__workspace_cache__: list[str] = []
        self.__clients_cache__: dict[str, dict[str, Any]] | None = None
        self._workspace_errors: set[str] = set()

        self._signaller = P4ConnectionManagerSignaller()

        if not use_progress_hander:
            return

        self._progress_handler = P4ProgressHandler(
            started_fn=started_fn,
            total_set_fn=total_set_fn,
            updated_fn=updated_fn,
            completed_fn=completed_fn,
        )
        self.p4.progress = self._progress_handler

    def __getattribute__(self, attribute_name) -> Any:
        """
        This is a custom handler for attribute access.

        It allows methods that need wrapping with
        `__run_connect__` to be wrapped when first called.
        The alternative was for `__run_connect__` to exist
        outside of P4ConnectionManager, which seemed janky.

        A method with the prefix `_connect_` will be wrapped
        with `__run_connect__` when first called and then assigned
        back to the instance without the `_connect_` prefix.
        This provides lazy creation and exposure of core methods.
        For example:
        This will expose the wrapped version of: `_connect_checkout`,
        saving it as an attribute on the `P4ConnectionManager`
        instance, to provide a quicker look up if accessed again:

        ```
        cm = P4ConnectionManager()
        cm.checkout
        ```

        It is recommended to use the full method name when
        calling from within the object (include `_connect_` prefix).
        This avoids unneccesary connection checks, providing a slight
        performance boost. I.E:
        `self._connect_checkout` rather than `self.checkout`
        """
        try:
            attribute = object.__getattribute__(self, attribute_name)
            return attribute

        except AttributeError:
            attribute_name = f"_connect_{attribute_name}"
            try:
                attribute = object.__getattribute__(self, attribute_name)
                if isinstance(attribute, MethodType):
                    __run_connect__ = object.__getattribute__(self, "__run_connect__")
                    attribute = __run_connect__(attribute)
                    object.__setattr__(self, attribute_name.replace("_connect_", ""), attribute)

                return attribute

            except AttributeError:
                _attribute_name = attribute_name.replace("_connect_", "")
                class_name = object.__getattribute__(self, "__class__").__name__
                raise AttributeError(f"{class_name} has no attribute: {_attribute_name}")

    # Properties:
    @property
    def p4(self) -> P4.P4:
        if self._p4 is None:
            self._p4 = P4.P4()
        return self._p4

    @property
    def host_name(self) -> str:
        if not self._host_name:
            self._host_name = socket.gethostname()
        return self._host_name

    @property
    def exceptions(self):
        return p4_errors.P4Exceptions

    @property
    def is_offline(self):
        return self._is_offline

    @property
    def offline_manager(self):
        if self._offline_manager is None:
            self._offline_manager = p4_offline.P4ConnectionManager()
        return self._offline_manager

    @property
    def _clients_cache(self) -> dict[str, dict[str, Any]]:
        if self.__clients_cache__ is None:
            host_name = self.host_name.lower()
            self.__clients_cache__ = {
                client["client"]: client
                for client in self.p4.run_clients("--me")
                if client["Host"].lower() == host_name
            }

        return self.__clients_cache__

    @property
    def _workspace_cache(self):
        if not self.__workspace_cache__:
            self.__workspace_cache__ = self._connect_get_workspaces()

        return self.__workspace_cache__

    # Protected Methods:
    @contextmanager
    def __connect__(self) -> Generator[P4.P4 | None, None, None]:
        """
        Context manager that connects to if not already connected p4,
        yielding the instance of p4 and closing the connection when done.
        """

        if self._is_offline:
            if not self._retry_p4_connection:
                yield
                return

        if not self.p4.connected():
            try:
                self.p4.connect()
                if self._is_offline:
                    self._signaller.connected.emit()
                    self._is_offline = False
            except Exception as error:
                if not self._is_p4_exception(error):
                    raise

                if "[P4.connect()] Connect to server failed; check $P4PORT" not in str(error):
                    raise

                self._is_offline = True
                self._signaller.disconnected.emit()
                self._start_retry_p4_connection_timer()
                yield
                return

        self._connection_depth += 1
        yield self.p4
        self._connection_depth -= 1
        if self._connection_depth == 0:
            self.__clients_cache__ = None
            self._process_errors()
            self._process_warnings()
            self.p4.disconnect()
            self._clear_errors()

    def __run_connect__(self, function):
        # type: (Callable[..., Any]) -> Callable[..., Any]
        """
        Decorator that connects to p4 before running a function.

        This is syntactic sugar to try and reduce indentation
        in a function body.
        Removing the need to use p4.connect in every function body:

        ```
        def function(self):
            with p4.connect():
                pass
        ```

        The intention is for this to work with P4ConnectionManager,
        it will not work with standard functions.
        """

        @functools.wraps(function)
        def _connect(*args, **kwargs):
            # type: (Any, Any) -> Any
            workspace_override = None
            args_info = self._get_path_arg_info(function, args) if args else (None, False)
            paths, compile_result = args_info
            paths, args, kwargs, workspace_override = self._split_args(paths, args, kwargs)

            with self.__connect__():
                if self._is_offline:
                    self.__run_function_offline__(
                        function, paths, compile_result, args, kwargs
                    )
                else:
                    self._update_workspace_cache(workspace_override or self.p4.client)
                    for workspace in self._workspace_cache:
                        with self.workspace_as(workspace):
                            self.__run_function__(
                                function, paths, workspace, compile_result, args, kwargs
                            )
                            if self._break_run_loop:
                                break

            if compile_result:
                return self.result

            _result = self.result
            if not _result:
                return _result

            if isinstance(_result, dict):
                _result = tuple(_result.values())

            if isinstance(_result, (list, tuple)) and len(_result) == 1:
                return _result[0]

            return _result

        return _connect

    def __run_function__(self, function, paths, workspace, compile_result, args, kwargs):
        # type: (Callable[..., Any], tuple[str, ...] | None, str, bool, tuple[Any], dict[str, Any]) -> None
        self.result = None
        self._break_run_loop = False
        self._run_successfully = False
        try:
            if paths and not self._are_paths_valid(paths, workspace):
                return

            is_get_stat = function == self._connect_get_stat
            result = function(*args, **kwargs)  # type: Any
            if is_get_stat:
                result = (result, ) if paths and len(paths) == 1 and paths[0].endswith("...") else result
            self.result = self._compile_result(compile_result, paths, result)
            self._run_successfully = True
            self._break_run_loop = True
            self._update_workspace_cache(workspace)
            return

        except p4_errors.P4PathDoesNotExistError as error:
            self._path_existence_errors.add(str(error))
            self._break_run_loop = True
            return

        except AttributeError as error:
            if "has no attribute" in str(error):
                raise

            raise AttributeError("P4.P4 has no attribute: '{0}' ".format(error))

        except Exception as error:
            if not self._is_p4_exception(error):
                raise

            # @sharkmob-shea.richardson:
            # As there are self.p4.warnings we can assume the
            # function ran correclty but it has triggered a warning.
            # This normally indicates that the correct workspace
            # has been used but there is an issue with the operation
            # so let's break out of the loop:
            if self.p4.warnings:
                self._run_successfully = True
                self._break_run_loop = True
                return

        return

    def __run_function_offline__(self, function, paths, compile_result, args, kwargs):
        # type: (Callable[..., Any], tuple[str, ...] | None, bool, tuple[Any], dict[str, Any]) -> None
        self.result = None
        result = self.offline_manager.run_function(function, args, kwargs)
        self.result = self._compile_result(compile_result, paths, result)

    # Private Methods:
    @staticmethod
    def _get_valid_path_objects(_paths: P4PathType) -> list[pathlib.Path]:
        def _is_valid_path(_path: Union[str, pathlib.Path]) -> bool:
            if isinstance(_path, str):
                _path = pathlib.Path(_path)

            # TODO: Make this more robust for people with bonkers folder setups.
            # The best we can do to determine if _potential_path is in
            # fact a path, is to see if it starts with "c:/":
            # This may fall over with people who have bonkers folder setups
            # But we can't solve for everything!
            _path_anchor_lower = _path.anchor.lower()
            if (not _path_anchor_lower.startswith("c:\\")) and (
                not _path_anchor_lower.startswith("\\\\")
            ):
                print(f"Path is invalid: {_path}")
                return False

            return True

        path_objects = (
            (pathlib.Path(_path) for _path in [_paths])
            if isinstance(_paths, (str, pathlib.Path))
            else (pathlib.Path(_path) for _path in _paths)
        )

        valid_paths = [path for path in path_objects if _is_valid_path(path)]
        return valid_paths

    @staticmethod
    def _get_correct_p4_paths(
        _paths: list[pathlib.Path],
    ) -> tuple[str]:
        """
        Test if the path exists test if it is a file.
            If the path doesn't exist and has an extension, then assume it is a file.
            This is to try and figure out if the path is a folder and append "/..." if so
        """

        out_paths: list[str] = []
        for _path in _paths:
            # Already declared as a directory:
            _path_str = str(_path)
            if _path_str.endswith("\\..."):
                out_paths.append(_path_str)
                continue

            # A depot path:
            if _path_str.startswith("\\\\"):
                if not _path.suffix:
                    _path_str = f"{_path_str}\\..."

                _path_str = _path_str.replace("\\", "/")
                out_paths.append(_path_str)
                continue

            is_file = True if _path.exists() and _path.is_file() else _path.suffix
            out_paths.append(_path_str if is_file else f"{_path}\\...")

        return tuple(out_paths)

    @staticmethod
    def _is_file_checked_out_by_current_user(data: dict[str, Any]) -> bool:
        if "action" in data and data["action"] == "add":
            return True
        if "action" in data and data["action"] == "edit":
            return True

        return False

    @staticmethod
    def _compile_result(compile_result, paths, result):
        # type: (bool, tuple[str] | None, Any | None) -> Any
        if compile_result and paths and isinstance(result, col_abc.Iterable):
            result = {path.replace("\\...", ""): data for path, data in zip(paths, result)}

        return result

    def _get_clean_p4_paths(self, paths: Iterable[str]):
        valid_paths = self._get_valid_path_objects(paths)
        return self._get_correct_p4_paths(valid_paths)

    def _split_args(self, paths, args, kwargs):
        # type: (tuple[str, ...] | None, tuple[Any, ...], dict[str, Any]) -> tuple[tuple[str,...] | None, tuple[Any, ...], dict[str, Any], str | None]  # noqa
        if paths:
            valid_paths = self._get_valid_path_objects(paths)
            paths = self._get_correct_p4_paths(valid_paths)
            _args = list(args[1:])
            _args.insert(0, paths)
            args = tuple(_args)

        workspace = None
        if "workspace_override" in kwargs:
            workspace = kwargs.pop("workspace_override")
            assert workspace is None or isinstance(workspace, str), (
                "workspace_override must be a string - got: {0} of type: {1}".format(
                    workspace, type(workspace)
                )
            )

        return paths, args, kwargs, workspace

    def _are_paths_valid(self, paths, workspace):
        # type: (tuple[Any, ...], str) -> bool
        paths = make_tuple_if_not(paths)
        if self._are_paths_under_root(workspace, paths):
            return True

        for path in paths:
            self._workspace_errors.add(str(path))

        return False

    @lru_cache(maxsize=64)
    def _get_workspace_roots(self, workspace: str) -> tuple[str, str]:
        """Get the roots of the given workspace"""

        if workspace not in self._clients_cache:
            # @sharkmob-shea.richardson:
            # Raise a P4Exception. If within the connect loop, will continue
            # to the next workspace. If in a standalone function will raise a
            # valid error. This handles the bug where client name is provided
            # instead of a valid workspace name.
            # This is a workaround rather than a fix as it is really hard to debug:
            raise P4.P4Exception(f"Invalid workspace name provided: '{workspace}'")

        client = self._clients_cache[workspace]
        assert "Root" in client, (
            f"'Root' not found for workspace: '{workspace}'' - it is likely a dead!:\n{client}"
        )
        client_root = client["Root"]
        server_info = self._connect_get_path_info([f"{client_root}\\..."])[0]
        server_root = server_info["depotFile"].rstrip("...")
        return (
            str(pathlib.Path(client_root)).lower(),
            str(pathlib.Path(server_root)).lower()
        )

    @lru_cache(maxsize=64)
    def _is_path_under_root(
        self, path: Union[str, pathlib.Path], client_root: str, server_root: str
    ) -> bool:
        path = str(path).lower()
        if path.startswith(server_root):
            return True

        elif path.startswith(client_root):
            return True

        return False

    # @lru_cache(maxsize=64)
    def _are_paths_under_root(self, workspace: str, paths: tuple[str | pathlib.Path]):
        client_root, server_root = self._get_workspace_roots(workspace)
        for path in paths:
            if self._is_path_under_root(path, client_root, server_root):
                continue

            return False

        return True

    @lru_cache(maxsize=64)
    def _is_path_under_any_root(self, path: Union[str, pathlib.Path]):
        for workspace in self._workspace_cache:
            with self.workspace_as(workspace):
                client_root, server_root = self._get_workspace_roots(workspace)
                if self._is_path_under_root(path, client_root, server_root):
                    return True
        return False

    @functools.lru_cache(maxsize=64)
    def _args_has_path_or_workspace(self, signature):
        # type: (inspect.Signature) -> bool
        """
        Test if the function to be wrapped has an argument
        called `path`, returning True if so and False if not.
        This will determine if path pre processing functions
        should be run on the functions args or not.

        This is cached to provide the best possible performance.
        """

        if "path" not in signature.parameters and "workspace" not in signature.parameters:
            return False

        return True

    @functools.lru_cache(maxsize=64)
    def _get_path_index_from_args(self, signature):
        # type: (inspect.Signature) -> int | None
        arg_names = tuple(signature.parameters)
        path_index = None
        if "path" in arg_names:
            path_index = arg_names.index("path")

        return path_index

    def _set_retry_p4_connection(self, value: bool):
        self._retry_p4_connection = value

    def _start_retry_p4_connection_timer(self, interval=5):
        timer = threading.Timer(interval, self.test_connection)
        timer.start()

    def _update_workspace_cache(self, workspace):
        """
        This puts the workspace that most recently worked at the
        front of the `_workspace_cache` to try and reduce
        the number of attempts on subsequent operations.
        The idea is p4 operations work on batches of files
        within the same workspace.
        This won't always be the case, but it will make
        large speed improvements when it is:
        """
        if workspace not in self._workspace_cache:
            print("Workspace is not valid: {} - cannot sort cache".format(workspace))
            return

        index = self._workspace_cache.index(workspace)
        if index:
            self._workspace_cache.pop(index)
            self._workspace_cache.insert(0, workspace)

    def _get_path_arg_info(self, function, args):
        # type: (Callable[..., Any], tuple[Any, ...]) -> tuple[tuple[str] | None, bool]
        signature = inspect.signature(function)
        compile_result = False
        if not self._args_has_path_or_workspace(signature):
            return None, compile_result

        path = None   # type: tuple[str] | None
        path_index = self._get_path_index_from_args(signature)
        if path_index is not None:
            _path = args[path_index]
            compile_result = isinstance(_path, (list, tuple))
            _path = make_tuple_if_not(_path)
            path = tuple(dict.fromkeys(_path).keys())

        return path, compile_result

    def _is_p4_exception(self, error):
        # type: (Exception) -> bool
        """
        Query the exception type by `__name__` as it seems
        that P4 can get confused if there are multiple P4
        module paths available which results in P4Exception not
        being caught as expected!
        """
        return type(error).__name__ == "P4Exception"

    def _clear_errors(self) -> None:
        self._attribute_errors.clear()
        self._workspace_errors.clear()

    def _process_errors(self) -> None:
        if self._run_successfully:
            return

        extra_path_existence_errors = []

        def _process_workspace_errors(_extra_path_existence_errors):
            if self.p4.errors and not self._attribute_errors:
                if not self._workspace_errors:
                    return False

                error_text = "The paths do not exist under a valid workspace root:"
                invalid_paths_found = False
                for path in self._workspace_errors:
                    if not self._is_path_under_any_root(path):
                        error_text = f"{error_text}\n - {path}"
                        invalid_paths_found = True

                if not invalid_paths_found:
                    for path in self._workspace_errors:
                        if not pathlib.Path(path).exists():
                            _extra_path_existence_errors.append(path)

                    if not _extra_path_existence_errors:
                        return False

                else:
                    error_text = f"{error_text}\n"
                    sys.stderr.write(error_text)
                    return True

        def _process_path_existence_errors(_extra_path_existence_errors):
            _path_existence_errors = self._path_existence_errors.copy()
            _path_existence_errors.union(_extra_path_existence_errors)
            if _path_existence_errors:
                error_text = "The following paths do not exist:"
                for path in _path_existence_errors:
                    error_text = f"{error_text}\n - {path}"

                error_text = f"{error_text}\n"
                sys.stderr.write(error_text)

        def _process_p4_attribute_errors():
            if self._attribute_errors:
                error_text = "The following p4 attributes do not exist:"
                for error in self._attribute_errors:
                    error_text = f"{error_text}\n - {error}"

                error_text = f"{error_text}\n"
                sys.stderr.write(error_text)

        def _process_errors():
            if self.p4.errors:
                error_text = "The following errors occured:"
                for error in self.p4.errors:
                    error_text = f"{error_text}\n - {error}"

                error_text = f"{error_text}\n"
                sys.stderr.write(error_text)

        if _process_workspace_errors(extra_path_existence_errors):
            return

        _process_path_existence_errors(extra_path_existence_errors)
        _process_p4_attribute_errors()
        _process_errors()

    def _process_warnings(self) -> None:
        warnings = self.p4.warnings
        if not warnings:
            return

        exclusive_check_outs = []
        for warning in warnings:
            if " - can't edit exclusive file already opened" in warning:
                exclusive_check_outs.append(warning.split(" -")[0])

        if exclusive_check_outs:
            raise p4_errors.P4ExclusiveCheckoutError(exclusive_check_outs)

        warning_text = "The following warnings occurred:"
        warning_added = False
        for warning in warnings:
            warning = str(warning)
            # if " - no such file(s)" in warning:
            #     continue

            warning_added = True
            warning_text = f"{warning_text}\n {warning}"

        if warning_added:
            warning_text = f"{warning_text}\n"
            sys.stdout.write(warning_text)

        # warnings.clear()

    if _typing:

        @typing.overload
        def _process_result(
            self,
            result,
            keys,
            actions,
            none_keys=None,
            none_actions=None,
            true_pattern=...,
            false_pattern=...,
            set_none=False
        ):
            # type: (T_Result, T_Keys, T_Actions, T_NoneKeys, T_NoneActions, str, str, Literal[False]) -> list[bool]  # noqa
            ...

        @typing.overload
        def _process_result(
            self,
            result,
            keys,
            actions,
            none_keys=None,
            none_actions=None,
            true_pattern=...,
            false_pattern=...,
            set_none=True
        ):
            # type: (T_Result, T_Keys, T_Actions, T_NoneKeys, T_NoneActions, str, str, Literal[True]) -> list[bool | None]  # noqa
            ...

    def _process_result(
        self,
        result,
        keys,
        actions,
        none_keys=None,
        none_actions=None,
        true_pattern="",
        false_pattern="",
        set_none=False
    ):
        # type: (T_Result, T_Keys, T_Actions, T_NoneKeys, T_NoneActions, str, str, Literal[True, False]) -> list[bool | None] | list[bool]  # noqa
        """
        Process the given result, matching expected key & action pairs for
        dictionary results or true or false patterns for string results
        to determine if the result has been successful or not.
        """

        keys = make_tuple_if_not(keys)
        actions = make_tuple_if_not(actions)
        none_keys = make_tuple_if_not(none_keys) if none_keys else tuple()
        none_actions = make_tuple_if_not(none_actions) if none_actions else tuple()

        def query_key(data, keys, actions, none_keys, none_actions, result, set_none=False):
            # type: (dict[str, str], tuple[str], tuple[str], tuple[str], tuple[str], list[bool | None], bool) -> None  # noqa
            if set_none:
                for key in none_keys:
                    if key not in data:
                        continue

                    value = data[key]
                    if value in none_actions:
                        result.append(None)
                        return

            for key in keys:
                if key not in data:
                    continue

                value = data[key]
                if isinstance(value, list):
                    value = value[0]

                result.append(value in actions)
                return

            result.append(False)

        results = []  # type: list[bool | None]
        for data in result:
            if not data and set_none:
                results.append(None)
                continue

            if isinstance(data, dict):
                query_key(data, keys, actions, none_keys, none_actions, results, set_none=set_none)
                continue

            if isinstance(data, str):
                if true_pattern and true_pattern in data:
                    results.append(True)
                    continue

                if false_pattern and false_pattern in data:
                    results.append(False)
                    continue

                elif "- empty, assuming" in data:
                    continue

            results.append(False)
            break

        return results

    # Connect Methods:
    def _connect_add(
        self,
        path: T_PthStrLst,
        change_description: str | None = None,
    ) -> P4ReturnBoolType:
        """
        Add the given file if it does not exists on the server already.
        """

        for _path in path:
            if not pathlib.Path(_path).exists():
                raise p4_errors.P4PathDoesNotExistError(_path)

        result = self.p4.run_add(path)
        if change_description:

            def _get_path_to_reopen(data):
                # type: (str) -> str | None
                if "already opened for edit" in data:
                    return data.split(" - ")[0]

                if "currently opened for add" in data:
                    return data.split("#")[0]

            files_to_reopen = []  # type: list[str]
            for _result in result:
                if isinstance(_result, dict):
                    continue

                path_to_reopen = _get_path_to_reopen(_result)
                if not path_to_reopen:
                    continue

                files_to_reopen.append(path_to_reopen)

            if files_to_reopen:
                self.p4.run_reopen(["-c", "default"], files_to_reopen)

            self._connect_create_change_list(change_description, files=path)

        return self._process_result(
            result,
            "action",
            "add",
            true_pattern="- currently opened for"
        )

    def _connect_add_to_change_list(self, path: T_PthStrLst, description: str) -> bool:
        change_dict = self._connect_get_existing_change_list(description)
        user_name = self._connect_get_user_name()
        client = self.p4.client
        changes: list[dict[str, Any]] = self.p4.run_changes(
            ["-u", user_name, "-c", client, "-s", "pending"]
        )
        exists = self._connect_exists_on_server(path)
        paths_to_add = [path[index] for index, exist in enumerate(exists) if not exist]
        if paths_to_add:
            self._connect_add(paths_to_add)

        depot_paths = self._connect_get_server_path(path)

        self._connect_checkout(path)
        _depot_paths = set((path for path in depot_paths if path))
        paths_to_reopen = []  # type: list[str]
        changes = self.p4.run_describe([change["change"] for change in changes])
        for change in changes:
            if "depotFile" not in change:
                continue

            if change["desc"] == description:
                continue

            intersection = _depot_paths.intersection(
                set(change["depotFile"])
            )
            if not intersection:
                continue

            paths_to_reopen.extend(intersection)

        if paths_to_reopen:
            self.p4.run_reopen(
                ["-c", "default"], paths_to_reopen
            )

        files = [info["depotFile"] for info in self.p4.run_where(path)]
        change_files = (
            change_dict["Files"]
            if "Files" in change_dict
            else []
        )  # type: list[str]
        change_files.extend(files)
        change_files = list(set(change_files))
        change_dict["Files"] = change_files

        _result = self.p4.save_change(change_dict)
        result = self._process_result(
            _result,
            "",
            "",
            true_pattern=f"adding {len(change_files)} file(s)."
        )
        return result[0]

    def _connect_checkout(
        self,
        path: T_PthStrLst,
        change_description: str | None = None,
    ) -> bool | list[bool] | None:
        """
        Checkout the given file(s).
        """

        stat = self._connect_get_stat(path)
        path = tuple((_stat["depotFile"] for _stat in stat if _stat))

        result = self._connect_is_latest(path)
        paths_to_sync = [path for path, is_latest in zip(path, result) if is_latest is False]
        if paths_to_sync:
            self._connect_sync(paths_to_sync)

        edit_result = self.p4.run_edit(path)
        if change_description:
            self._connect_create_change_list(change_description, files=path)

        _result = self._process_result(
            edit_result,
            "action",
            "edit",
            true_pattern="- currently opened for",
            false_pattern="- can't edit (already opened for add)",
        )
        if _result is None:
            return None

        return _result

    def _connect_checked_out_by(
        self, path: T_PthStrLst, other_users_only: bool = False, fstat_args: P4ArgsType = None
    ) -> list[list[tuple[str, str]] | None]:
        stat = self._connect_get_stat(path, fstat_args or [])
        current_user_name = self._connect_get_user_name() if not other_users_only else ""
        checked_out_by_list: list[list[tuple[str, str]] | None] = []
        for data in stat:
            if not data:
                checked_out_by_list.append(None)
                continue

            file_checked_out_by_list: list[str] = []
            if (not other_users_only) and self._is_file_checked_out_by_current_user(data):
                # @sharkmob-shea.richardson:
                # Format this in the same way as if it were checked out by another user, so
                # the output will be consistent:
                file_checked_out_by_list.append(f"{current_user_name}@{self.p4.client}")

            if "otherOpen" in data:
                file_checked_out_by_list.extend(data["otherOpen"])

            if not file_checked_out_by_list:
                checked_out_by_list.append(None)
                continue

            clean_file_checked_out_by_list = [
                tuple(user_name.split("@")) for user_name in file_checked_out_by_list
            ]
            checked_out_by_list.append(clean_file_checked_out_by_list)

        return checked_out_by_list

    def _connect_create_change_list(
        self,
        description: str,
        files: T_PthStrLst | None = None,
        files_to_reopen: T_PthStrLst | None = None
    ) -> list[bool]:
        """
        Create a change list with the given description and optional files.
        """

        try:
            change_dict = self._connect_get_existing_change_list(description)
        except P4.P4Exception:
            change_dict = None

        _files = []
        if files:
            files = (
                [file for file in files if file not in files_to_reopen]
                if files_to_reopen
                else files
            )
            _files = [info["depotFile"] for info in self.p4.run_where(files)]

        if change_dict:
            change_files = (
                change_dict["Files"]
                if "Files" in change_dict
                else []
            )  # type: list[str]
            change_files.extend(_files)
            change_files = list(set(change_files))
            change_dict["Files"] = change_files

        else:
            change_dict = self.p4.fetch_change()
            if not change_dict:
                raise P4.P4Exception("Failed to create a new change list")

            change_dict["Files"] = _files

        if files_to_reopen:
            self.p4.run_reopen(
                ["-c", description], files_to_reopen
            )

        change_dict["Description"] = description
        save_change_result = self.p4.save_change(change_dict)
        result = self._process_result(
            save_change_result, "", "", true_pattern="created."
        )

        return result

    def _connect_get_change_list_number(self, description: str):
        change_dict = self._connect_get_existing_change_list(description)
        if not change_dict:
            return

        return change_dict["Change"]

    def _connect_create_workspace(self, name: str, root: str, stream: str):
        client = self.p4.fetch_client()
        client["Client"] = name
        client["Root"] = root
        client["Stream"] = stream
        return self.p4.save_client(client)

    def _connect_delete(
        self,
        path: T_PthStrLst,
        change_description: str | None = None,
    ) -> list[bool]:
        """
        Delete the given file if it exists on the server.
        """

        if change_description:
            change_number = self._connect_create_change_list(change_description)
            result = self.p4.run_delete(["-c", change_number, path])
        else:
            result = self.p4.run_delete(path)

        return self._process_result(result, "action", "edit")

    def _connect_delete_change_list(self, description: str, force: bool = False) -> list[bool]:
        """
        Delete a change list based on it's description.
        """

        change_list = self._connect_get_existing_change_list(description)
        change_id = int(change_list["Change"])
        files = "Files" in change_list and change_list["Files"]
        if files and force:
            self.p4.run_reopen(["-c", "default"], files)

        change_result = self.p4.run_change(["-d", change_id])  # type: list[str]
        result = self._process_result(
            change_result,
            "",
            "",
            true_pattern=f"Change {change_id} deleted.",
            false_pattern="open file(s) associated with it and can't be deleted"
        )

        return result

    def _connect_exists_on_server(self, path: T_PthStrLst) -> list[bool]:
        # @sharkmob-shea.richardson:
        # If self.path is a directory, limit the number of
        # returned files from the fstat query, to avoid getting
        # info on all sub files recursively. This is done by
        # passing in the -m (max) argument and setting it as 1:
        stat = self._connect_get_stat(path, ["-m 1"])
        result = [True if "depotFile" in data else False for data in stat]
        return result

    def _connect_get_attribute(
        self,
        path: T_PthStrLst,
        name: str,
        default: Any = None,
        raise_error:bool = False
    ) -> list[str | None]:
        # -Oa flag: Output attributes set by p4 attribute.
        result: list[dict[str, str]] = self.p4.run_fstat(("-Oa",), path)

        def _get_attribute(data: dict[str, str], name: str):
            for key, value in data.items():
                if "-" in key and name in key:
                    return value

            if raise_error:
                raise p4_errors.P4AttributeError(f"'{name}' on: '{data['depotFile']}'")

            self._attribute_errors.add(f"'{name}' on: '{data['depotFile']}'")

            return default

        return [_get_attribute(_result, name) for _result in result]

    def _connect_get_client_root(self):
        result = self.p4.run_info()
        return result[0]["clientRoot"]

    def _connect_get_current_client_revision(self, path: T_PthStrLst) -> list[int | None]:
        """
        Get the current client revision numbers for the given path/paths.
        """

        stat = self._connect_get_stat(path)
        result = [int(data["haveRev"]) if ("haveRev" in data) else 0 if data else None for data in stat]
        return result

    def _connect_get_version_info(self, path: T_PthStrLst) -> list[tuple[int, int] | tuple[None, None]]:
        return self._connect_get_current_revision_info(path)

    def _connect_get_current_revision_info(self, path: T_PthStrLst) -> list[tuple[int, int] | tuple[None, None]]:
        """
        Get the current source and client revision numbers for the given path/paths.
        """

        def _get_version_info(stat: dict[str, str]) -> tuple[int, int] | tuple[None, None]:
            if not stat:
                return (None, None)

            source_rev = stat["headRev"] if "headRev" in stat else 0
            local_rev = stat["haveRev"] if "haveRev" in stat else 0
            return int(source_rev), int(local_rev)

        stat = self._connect_get_stat(path)

        return [_get_version_info(data) for data in stat]

    def _connect_get_current_server_revision(self, path: T_PthStrLst) -> list[int | None]:
        """
        Get the current source revision numbers for the given path/paths.
        """

        stat = self._connect_get_stat(path)
        result = [int(data["headRev"]) if ("headRev" in data) else 0 if data else None for data in stat]
        return result

    def _connect_get_existing_change_list(self, description: str) -> dict[str, Any]:
        user_name = self._connect_get_user_name()
        client = self.p4.client
        changes: list[dict[str, Any]] = self.p4.run_changes(
            ["-u", user_name, "-c", client, "-s", "pending"]
        )

        if not changes:
            raise P4.P4Exception("No changelists found!")

        description = description.strip()
        for change_data in self.p4.run_describe([change["change"] for change in changes]):
            if description != change_data["desc"].strip():
                continue

            return self.p4.fetch_change(change_data["change"])

        raise P4.P4Exception(f'No changelist with description: "{description}" found!')

    def _connect_get_files(
        self, path: T_PthStrLst, extension: str | None = None, include_all: bool = False, query_sub_folders: bool = True
    ) -> list[tuple[pathlib.Path, ...]]:
        extension = extension or ""
        if isinstance(path, list):
            path = [f"{_path}{extension}" for _path in path]

        def _is_file_valid(_path, parent_path):
            if query_sub_folders:
                return True

            return _path.parent == parent_path

        result = []
        for _path in path:
            args = _path if include_all else [["-e"], _path]
            files = (pathlib.Path(data["depotFile"]) for data in self.p4.run_files(args))
            result.append(tuple((file for file in files if _is_file_valid(file, _path))))

        return result

    def _connect_get_files_in_folder_in_date_order(
        self,
        path: T_PthStrLst,
        name_pattern: str | None = None,
        extensions: Iterable[str] | None = None,
        fstat_args: Iterable[str] | None = None,
    ) -> list[tuple[P4PathDateData]]:
        result: list[tuple[P4PathDateData]] = []
        fstat_args = list(fstat_args) if fstat_args else []
        # -Sd: Sort by date.
        # -Rc: Limit output to files mapped into the current workspace.
        fstat_args.extend(("-Sd", "-Rc"))
        for _path in path:
            if not _path.endswith("..."):
                raise AttributeError(
                    "get_files_in_folder_in_date_order can only be run on folders!"
                )

            stat = self._connect_get_stat((_path, ), args=fstat_args)
            if name_pattern:
                name_pattern = name_pattern.lower()

            _extensions = None
            if extensions is not None:
                _extensions = set(
                    (
                        extension.lower()
                        if extension.startswith(".")
                        else ".{}".format(extension).lower()
                        for extension in extensions
                    )
                )

            local_path = self._connect_get_local_path((_path, ))
            if not local_path:
                continue

            _local_path = local_path[0]
            parent_path_client = pathlib.Path(_local_path)
            path_result: list[P4PathDateData] = []
            for data in stat:
                path_date_data = P4PathDateData()
                if not data:
                    path_date_data.set_data(None, None)

                else:

                    local_path = pathlib.Path(data["clientFile"])
                    if not local_path.parent == parent_path_client:
                        continue

                    if name_pattern and name_pattern not in local_path.stem.lower():
                        continue

                    if _extensions and local_path.suffix.lower() not in _extensions:
                        continue

                    if "action" in data and data["action"] == "add":
                        # @sharkmob-shea.richardson:
                        # As the file has been marked for add,
                        # all we have to go on is the last time
                        # the file was modified locally:
                        mod_time = local_path.stat().st_mtime
                        mod_date = datetime.datetime.fromtimestamp(mod_time)
                        path_date_data.set_data(local_path, mod_date)

                    else:
                        mod_time = int(data["headTime"])
                        mod_date = datetime.datetime.fromtimestamp(mod_time)
                        path_date_data.set_data(local_path, mod_date)

                path_result.append(path_date_data)

            result.append(tuple(path_result))

        return result

    def _connect_get_info(self):
        return self.p4.run_info()

    def _connect_get_latest(self, path: T_PthStrLst) -> list[bool | None]:
        try:
            sync_result = self.p4.run_sync(path)
            result = self._process_result(sync_result, "action", ("updated", "added"), set_none=True)
            return result
        except Exception as error:
            if not self._is_p4_exception(error):
                raise

            if not self.p4.warnings:
                raise

            # @sharkmob-shea.richardson:
            # Sync has failed, potentially due to one or more of the files
            # not existing on p4. Let's filter those files out of `path`
            # and try sync again:
            warnings = self.p4.warnings.copy()  # type: list[str]
            result = [True] * len(path)  # type: list[bool | None]
            latest_paths = tuple(
                (
                    (warning.replace(" - file(s) up-to-date.", ""), warnings.remove(warning))[0]
                    for warning in reversed(warnings)
                    if "file(s) up-to-date." in warning
                )
            )

            # @sharkmob-shea.richardson:
            # All paths are already latest, so lets exit:
            if len(latest_paths) == len(path):
                return result

            local_paths = tuple(
                (
                    (warning.replace(" - no such file(s).", ""), warnings.remove(warning))[0]
                    for warning in reversed(warnings)
                    if "no such file(s)." in warning
                )
            )
            if local_paths:
                for _path in local_paths:
                    index = path.index(_path)
                    result[index] = None

            return result

    def _connect_get_local_path(self, path: T_PthStrLst) -> tuple[str]:
        return tuple((data["path"].rstrip("...") for data in self.p4.run_where(path)))

    def _connect_get_newest_file_in_folder(
        self,
        path: T_PthStrLst,
        name_pattern: str | None = None,
        extensions: Iterable[str] | None = None,
    ):
        paths = self._connect_get_files_in_folder_in_date_order(
            path, name_pattern=name_pattern, extensions=extensions
        )
        if not paths:
            return

        if not paths[0]:
            return

        return paths[0][-1]

    def _connect_get_path_locations(self, path: T_PthStrLst) -> P4ReturnType:
        return self._connect_get_path_info(path)

    def _connect_get_path_info(self, path: T_PthStrLst) -> P4ReturnType:
        return self.p4.run_where(path)

    def _connect_get_revision(
        self,
        path: T_PthStrLst,
        revision: int | tuple[int],
    ) -> list[bool]:
        if not isinstance(revision, (list, tuple)):
            revision = tuple([revision] * len(path))

        if not len(revision) == len(path):
            raise AttributeError(f"revision count ({len(revision)}) must match path count({len(path)})!")

        sync_result = self.p4.run_sync([f"{_path}#{_revision}" for _path, _revision in zip(path, revision)])
        result = self._process_result(
            sync_result,
            "action",
            ("updated", "deleted"),
            true_pattern=" - file(s) up-to-date."
        )

        return result

    def _connect_get_revision_history(self, path: T_PthStrLst, include_all: bool = False):
        args = ["-t"]
        # if not include_all:
        #     args.append("-s")

        # args_str = " ".join(args)
        # command = f"{args_str} filelog"
        return self.p4.run_filelog(args, path)
        # return self._connect_run_command(command, path)

    def _connect_get_server_path(self, path: T_PthStrLst) -> list[str | None]:
        return [data["depotFile"] if data else None for data in self.p4.run_where(path) if data]

    def _connect_get_stat(
        self, path: str | Sequence[str], args: P4ArgsType = None
    ) -> list[dict[str, str]]:

        args = args or []
        try:
            # @sharkmob-shea.richardson:
            # We query fstat of all the given paths.
            # In most cases this will be a valid path or paths.
            # If the path is invalid, ie doesn't exist, then this
            # will throw an exception
            stat = self.p4.run_fstat([args, path])
        except Exception as error:
            if not self._is_p4_exception(error):
                raise

            def _cull_no_such_file_warnings(index, warning, warnings_count):
                # type: (int, str, int) -> str
                index = warnings_count - index
                self.p4.warnings.pop(index)
                return warning.replace(" - no such file(s).", "")

            # @sharkmob-shea.richardson:
            # fstat has failed, potentially due to one or more of the files
            # not existing on p4. Let's filter those files out of `path`
            # and try fstat again:
            path = typing.cast(T_StrTuple, path)
            warnings = tuple(reversed(self.p4.warnings))
            warnings_count = len(warnings) - 1
            excluded_paths = (
                _cull_no_such_file_warnings(index, warning, warnings_count)
                for index, warning in enumerate(warnings)
                if "no such file(s)." in warning
            )  # type: Generator[str, None, None]
            exclude_data = {path.index(excluded_path): excluded_path for excluded_path in excluded_paths}
            p4_path = tuple(filter(lambda i: i not in exclude_data.values(), path))
            stat: list[dict[str, Any]] = self.p4.run_fstat([args, p4_path]) if p4_path else []

            # @sharkmob-shea.richardson:
            # we now need to add an empty dict into the indicies of
            # the files that don't exist in perforce to allow
            # the results to be mapped correctly when returned
            # from __connect__
            empty_dict = {}
            for index in sorted((exclude_data.keys())):
                stat.insert(index, empty_dict)

        return stat

    def _connect_get_streams(self) -> tuple[str]:
        streams = self.p4.run_streams()
        return tuple((stream["Stream"] for stream in streams))

    def _connect_get_user_name(self) -> str:
        user_data = self.p4.run_user("-o")[0]
        return user_data["User"] if user_data and "User" in user_data else ""

    def _connect_get_workspaces(self, stream: str | None = None) -> list[str]:
        host_name = self.host_name.lower()
        client_data = self.p4.run_clients("--me")
        if stream:
            stream = stream.lower()
            workspaces = (
                data["client"]
                for data in client_data
                if data["Host"].lower() == host_name and data["Stream"].lower() == stream
            )

        else:
            workspaces = (data["client"] for data in client_data if data["Host"].lower() == host_name)

        workspaces = list(dict.fromkeys(workspaces).keys())
        return workspaces

    def _connect_is_checked_out_by_user(
        self, path: T_PthStrLst, user_name: tuple[str] | str | None = None
    ) -> list[bool]:
        result: list[bool] = []
        checked_out_by = self._connect_checked_out_by(path)
        user_names = None if user_name is None else make_tuple_if_not(user_name)
        user_names = set(user_names or (self._connect_get_user_name(),))
        for _checked_out_by in checked_out_by:
            if _checked_out_by is None:
                result.append(False)
                continue

            user_found = False
            checked_out_by_set = set((name for name, _ in _checked_out_by))
            for user_name in user_names:
                if user_name in checked_out_by_set:
                    user_found = True
                    break

            if user_found:
                result.append(True)
                continue

            result.append(False)

        return result

    def _connect_is_checked_out(self, path: T_PthStrLst) -> list[bool | None]:
        stat_result = self._connect_get_stat(path)
        result = self._process_result(
            stat_result,
            ("otherAction", "action"),
            ("edit", "add"),
            none_keys=("headAction", ),
            none_actions=("delete", ),
            set_none=True
        )

        return result

    def _connect_is_latest(self, path):
        # type: (Sequence[str]) -> tuple[bool | None]
        result = dict.fromkeys(path, False)  # type: dict[str, bool | None]
        files = []  # type: list[str]
        folders = []  # type: list[str]
        for _path in path:
            if _path.endswith("..."):
                folders.append(_path)
                continue
            files.append(_path)

        if folders:
            def _is_folder_latest(folder):
                # type: (str) -> bool | None
                # @sharkmob-shea.richardson
                # We have to test each folder individually else P4
                # condenses all the returned statistics into one.
                # This makes it impossible to work out which folders
                # need syncing and which do not.
                try:
                    sync_result = self.p4.run_sync(("-N"), folder)[0]
                except Exception as error:
                    if not self._is_p4_exception(error):
                        raise

                    return None

                change_count_str = sync_result.split("=")[1]  # type: str
                change_count_str = change_count_str.split(",")[0]
                change_counts = (bool(int(value)) for value in change_count_str.split("/"))
                return not any(change_counts)

            for folder in folders:
                result[folder] = _is_folder_latest(folder)

        stat = self._connect_get_stat(files)
        valid_states = {"add", "move/add", "edit"}
        def _is_file_latest(data):
            # type: (dict) -> bool | None
            if not data:
                return
            if "action" in data and data["action"] in valid_states:
                return True
            if "headRev" not in data:
                return False
            if "haveRev" not in data:
                return False

            return data["headRev"] == data["haveRev"]

        for file, data in zip(files, stat):
            is_latest = _is_file_latest(data)
            result[file] = is_latest

        return tuple(result.values())

    def _connect_is_stream_valid(self, stream: str) -> bool:
        streams = self._connect_get_streams()
        return stream.lower() in set([stream.lower() for stream in streams])

    def _connect_move(
        self,
        path: T_PthStrLst,
        target_path: T_PthStrLst,
        change_description: str | None = None,
        get_latest: bool = True
    ) -> list[bool]:
        target_path = make_tuple_if_not(target_path)  # type: ignore
        clean_paths = self._get_clean_p4_paths(target_path)
        if get_latest:
            paths_to_sync = list(path).copy()
            paths_to_sync.extend(
                (
                    path for path
                    in clean_paths
                    if pathlib.Path(path).exists()
                )
            )
            if paths_to_sync:
                sync_result = {}
                try:
                    sync_result = self._connect_get_latest(paths_to_sync)
                except P4.P4Exception:
                    pass

                for result in paths_to_sync:
                    if sync_result is False:
                        raise P4.P4Exception("Files are not the latest versions!")

        path = typing.cast(T_StrTuple, path)
        if len(path) != len(clean_paths):
            raise ValueError("path length must equal target_path length")

        self._connect_checkout(path, change_description=change_description)
        args = []
        if change_description:
            change_number = self._connect_get_change_list_number(change_description)
            args.extend(("-c", change_number))

        move_result = []
        for source, target in zip(path, target_path):
            _args = args.copy()
            _args.extend((source, target))
            result = self.p4.run_move(_args)
            move_result.append(result[0])

        result = self._process_result(
            move_result,
            "action",
            "move/add",
            true_pattern="can't move (already opened for move/delete)"
        )

        return result

    def _connect_revert(self, path: T_PthStrLst) -> list[bool] | None:
        revert_result: list[dict[str, Any]] = self.p4.run_revert(path)
        _revert_result = (data for data in revert_result if data["clientFile"] in path or data["depotFile"] in path)
        result = self._process_result(
            _revert_result,
            "action",
            ("abandoned", "reverted", "deleted"),
            true_pattern="- currently opened for"
        )
        return result

    def _connect_run_command(self, cmd: str, *args, **kwargs):
        result = self.p4.run(cmd, *args, **kwargs)
        return result

    def _connect_set_attribute(self, path: T_PthStrLst, name: str, value: Any):
        attrubute_result = self.p4.run_attribute(("-n", name, "-v", value), path)
        result = self._process_result(attrubute_result, "status", "set")
        return result

    def _connect_submit_change_list(self, change_description: str) -> int | None:
        change_list_spec = self._connect_get_existing_change_list(change_description)
        result = self.p4.run_submit(change_list_spec)
        if not result:
            return None

        return int(result[0]["change"])

    def _connect_sync(self, path):
        """
        Synonym for get_latest
        """

        return self._connect_get_latest(path)

    def _connect_unsync(self, path: T_PthStrLst):
        _path = [f"{p}#none" for p in path] if isinstance(path, (list, tuple)) else f"{path}#none"
        sync_result = self.p4.run_sync(_path)
        result = self._process_result(sync_result, "action", "deleted")
        return result

    def _connect_update_change_list_description(self, old_description: str, new_description: str):
        change_list_spec = self._connect_get_existing_change_list(old_description)
        if not change_list_spec:
            raise P4.P4Exception("Changelist not found")

        change_list_spec["Description"] = new_description
        change_result = self.p4.save_change(change_list_spec)
        result = self._process_result(
            change_result, "", "", true_pattern=f"Change {change_list_spec['Change']} updated."
        )
        return result

    # Public Methods:
    @contextmanager
    def workspace_as(self, workspace: str) -> Iterator[None]:
        """Context manager that connects to if not already connected p4,
        yielding the instance of p4 and closing the connection when done.
        """

        current_workspace = self.p4.client
        try:
            self.p4.client = workspace
            yield

        except:
            raise

        finally:
            self.p4.client = current_workspace

    def test_connection(self) -> bool:
        try:
            with self.p4.connect():
                if self._is_offline:
                    self._signaller.connected.emit()
                    self._is_offline = False

                self._start_retry_p4_connection_timer(interval=60)
                return True

        except Exception as error:
            if not self._is_p4_exception(error):
                raise

            if not self._is_offline:
                self._is_offline = True
                self._signaller.disconnected.emit()

            self._start_retry_p4_connection_timer()
            return False


_connection_manager = None


def _get_connection_manager() -> P4ConnectionManager:
    if threading.current_thread() is not threading.main_thread():
        # Generate a new P4ConnectionManager per thread:
        return P4ConnectionManager()

    global _connection_manager
    if _connection_manager is None:
        _connection_manager = P4ConnectionManager()

    return _connection_manager


__all__ = (
    "_get_connection_manager",
    "P4ConnectionManager",
    "P4PathDateData",
    "exceptions",  # type: ignore
    "add",  # type: ignore
    "checkout",  # type: ignore
    "create_change_list",  # type: ignore
    "create_workspace",  # type: ignore
    "delete",  # type: ignore
    "delete_change_list",  # type: ignore
    "exceptions",  # type: ignore
    "get_attribute",  # type: ignore
    "checked_out_by",  # type: ignore
    "get_change_list_number",  # type: ignore
    "get_client_root",  # type: ignore
    "get_current_client_revision",  # type: ignore
    "get_current_revision_info",  # type: ignore
    "get_current_server_revision",  # type: ignore
    "get_existing_change_list",  # type: ignore
    "get_files",  # type: ignore
    "get_info",  # type: ignore
    "get_latest",  # type: ignore
    "get_local_path",  # type: ignore
    "get_newest_file_in_folder",  # type: ignore
    "get_path_info",  # type: ignore
    "get_revision",  # type: ignore
    "get_revision_history",  # type: ignore
    "get_server_path",  # type: ignore
    "get_stat",  # type: ignore
    "get_streams",  # type: ignore
    "get_user_name",  # type: ignore
    "get_workspaces",  # type: ignore
    "host_name",  # type: ignore
    "is_checked_out_by_user",  # type: ignore
    "is_checked_out",  # type: ignore
    "is_latest",  # type: ignore
    "is_offline",  # type: ignore
    "is_stream_valid",  # type: ignore
    "move",  # type: ignore
    "revert",  # type: ignore
    "run_command",  # type: ignore
    "set_attribute",  # type: ignore
    "submit_change_list",  # type: ignore
    "sync",  # type: ignore
    "test_connection",  # type: ignore
    "unsync",  # type: ignore
    "update_change_list_description",  # type: ignore
    "workspace_as",  # type: ignore
)


def __getattr__(attribute_name: str) -> Any:
    """
    Custom __getattr__ for this module that will return
    the method of the module level P4ConnectionManager.

        This achieves two things:
            1. Allows a single P4ConnectionManager to be used for one off calls
                in the main thread, without the need to init a new P4ConnectionManager
                for each call.
            2. Reduces the boilerplate required to expose the calls of the single
                P4ConnectionManager, whilst still making the functionality
                accessible at the module level.

        Args:
            attribute_name (str): The name of the module level attribute to access.

        Returns:
            Any: The accessed attribute.
    """

    connection_manager = _get_connection_manager()
    if hasattr(connection_manager, attribute_name):
        return getattr(connection_manager, attribute_name)

    _globals = globals()
    if attribute_name in _globals:
        return getattr(_globals, attribute_name)

    raise AttributeError(f"{__name__} has no attribute: {attribute_name}!")


def __dir__():
    return __all__


if __name__ == "__main__":
    pass
