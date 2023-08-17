import abc
import functools
import os
import pathlib
import six

from openpype.lib import local_settings

# @sharkmob-shea.richardson:
# This need to be evaluated at runtime to provide
# the correct type annotations for @class_property
# from typing import Generic
# from typing import TypeVar

# T1 = TypeVar("T1")
# T2 = TypeVar("T2")
_typing = False
if _typing:
    import datetime

    from typing import Callable
    from typing import Sequence
    from typing import Union

    T_P4PATH = Union[pathlib.Path, str, Sequence[Union[pathlib.Path, str]]]
del _typing




class ChangeListNotFoundError(Exception):
    pass


class ChangeListStillExistsError(Exception):
    def __init__(self, message):
        # type: (str) -> None

        message = "Change list still exists: {0} - this should be submitted first!".format(message)
        super().__init__(message)


# class class_property(Generic[T1, T2]):
#     """
#     A read only class property for use with < py39
#     """

#     def __init__(self, wrapped_function: Callable[..., T2]):
#         self.wrapped_function = wrapped_function

#     def __get__(self, _, owner_cls):
#         return self.wrapped_function(owner_cls)


def _save_file_decorator(function):
    # type: (Callable[[str], str]) -> Callable[[str], str]

    from . import get_active_vcs

    vcs = get_active_vcs()

    @functools.wraps(function)
    def save_file_wrapper(path):
        # type: (str) -> str
        if vcs is None:
            return function(path)

        vcs.checkout(path)
        return function(path)

    return save_file_wrapper


def _open_file_decorator(function):
    # type: (Callable[[str], str]) -> Callable[[str], str]
    @functools.wraps(function)
    def open_file_wrapper(path):
        # type: (str) -> str
        return function(path)

    return open_file_wrapper


@six.add_metaclass(abc.ABCMeta)
class VersionControl(object):
    """
    Base class for defining a version control interface.
    """

    _default_change_list_description = "Pyblish auto generated change list"

    def __init__(self):
        super(VersionControl, self).__init__()

        self._change_list_description = ""
        self._settings = None

    # Public Properties:
    @property
    def settings(self):
        # type: () -> local_settings.OpenPypeSettingsRegistry
        if self._settings is None:
            self._settings = local_settings.OpenPypeSettingsRegistry("version_control")

        return self._settings

    @property
    def saved_change_list_descriptions(self):
        try:
            return self.settings.get_item("change_list_descriptions")
        except ValueError:
            return {}

    @property
    def host_app_name(self):
        # type: () -> str
        """
        # Property:
        Get the name of the registerd host application
        """

        return os.environ["AVALON_APP"]

    @property
    def change_list_description_prefix(self):
        # type: () -> str
        """
        # Property:
        Get the prefix to be added to any given change list description.
        It follows the following convention:
        `[art][{parent}][{asset_name}][{task_type}][{task_name}]`

        This provides tags for UnrealGameSync.

        TODO: Have this be togglable via settings.
        TODO: Have this definable via the template system.
        """

        from openpype.pipeline import legacy_io

        legacy_io.install()
        project_name = legacy_io.Session["AVALON_PROJECT"]  # type: str
        asset_name = legacy_io.Session["AVALON_ASSET"]  # type: str
        task_name = legacy_io.Session["AVALON_TASK"]  # type: str

        project_entity = legacy_io.find_one({"type": "project", "name": project_name})
        assert project_entity, ("Project '{0}' was not found.").format(project_name)

        asset_entity = legacy_io.find_one(
            {"type": "asset", "name": asset_name, "parent": project_entity["_id"]}
        )
        assert asset_entity, ("No asset found by the name '{0}' in project '{1}'").format(
            asset_name, project_name
        )

        data = asset_entity["data"]

        asset_tasks = data.get("tasks") or {}
        task_info = asset_tasks.get(task_name) or {}
        task_type = task_info.get("type") or ""
        parents = data.get("parents") or []
        parent = "[{}]".format(parents[-1]) if parents else ""

        return "[Art]{p}[{an}][{tt}][{tn}]".format(
            p=parent, an=asset_name, tt=task_type, tn=task_name
        )

    @property
    def cached_change_list_description(self):
        # type: () -> str
        """
        # Property:
        Get the currently cached change list description for the current host.
        This will be the last description used, but only if the change list still
        exists. If the change list exists, the cached description will be returned.
        If the change list does not exists, the default change list description will
        be returned.
        """

        host_app_name = self.host_app_name
        change_list_descriptions = (
            self.saved_change_list_descriptions
        )  # type: dict[str, str] | None
        if not change_list_descriptions:
            return self._default_change_list_description

        change_list_description = change_list_descriptions.get(host_app_name)
        if not change_list_description:
            return self._default_change_list_description

        if not self.get_existing_change_list(change_list_description):
            return self._default_change_list_description

        return change_list_description

    @cached_change_list_description.setter
    def cached_change_list_description(self, value):
        # type: (str) -> None
        assert isinstance(
            value, str
        ), "cached_change_list_description must be an instance of {0}. Got: {1} of type: {type(value)}".format(
            str, value
        )

        change_list_descriptions = self.saved_change_list_descriptions
        change_list_descriptions[self.host_app_name] = value
        change_list_descriptions = self.settings.set_item(
            "change_list_descriptions", change_list_descriptions
        )

    @property
    def save_file_decorator(self):
        # type: () -> Callable[[Callable[[str], str]], Callable[[str], str]]
        return _save_file_decorator

    @property
    def open_file_decorator(self):
        # type: () -> Callable[[Callable[[str], str]], Callable[[str], str]]
        return _open_file_decorator

    @property
    def change_list_description(self):
        # type: () -> str
        """
        #Property:
        The current change list comment, if one has been set.
        This allows recovery of a change list comment if the publish process
        fails or the user chooses not to submit the change list.
        """

        _change_list_description = self._change_list_description
        if not _change_list_description:
            _change_list_description = self.cached_change_list_description

        if not _change_list_description.startswith("["):
            _change_list_description = "{0} {1}".format(
                self.change_list_description_prefix, _change_list_description
            )

        self._change_list_description = _change_list_description

        return _change_list_description

    @change_list_description.setter
    def change_list_description(self, value):
        # type: (str) -> None
        assert isinstance(
            value, str
        ), "change_list_description must be an instance of {0}. Got: {1} of type: {type(value)}".format(
            str, value
        )
        if value == self._change_list_description:
            return

        if not value.startswith("["):
            value = value[1:] if value.startswith(" ") else value
            value = "{0} {1}".format(self.change_list_description_prefix, value)

        self.cached_change_list_description = value
        self._change_list_description = value

    # Public Abstract Static Methods:
    @staticmethod
    @abc.abstractmethod
    def get_server_version(path):
        # type: (T_P4PATH) -> int
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def get_local_version(path):
        # type: (T_P4PATH) -> int
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def get_version_info(path):
        # type: (T_P4PATH) -> tuple[int | None, int | None]
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def get_files_in_folder_in_date_order(path, name_pattern=None, extensions=None):
        # type: (T_P4PATH, str | None, Sequence[str] | None) -> list[tuple[pathlib.Path, datetime.datetime]]
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def get_newest_file_in_folder(path, name_pattern=None, extensions=None):
        # type: (T_P4PATH, str | None, Sequence[str] | None) -> pathlib.Path | None
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def is_latest_version(path):
        # type: (T_P4PATH) -> bool
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def is_checkedout(path):
        # type: (T_P4PATH) -> bool
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def checked_out_by(path, other_users_only=False):
        # type: (T_P4PATH, bool) -> list[str] | None
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def exists_on_server(path):
        # type: (T_P4PATH) -> bool
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def sync_latest_version(path):
        # type: (T_P4PATH) -> bool
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def sync_to_version(path, version):
        # type: (T_P4PATH, int) -> bool
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def add(path, comment=""):
        # type: (T_P4PATH, str) -> bool
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def add_to_change_list(path, comment):
        # type: (T_P4PATH, str) -> bool
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def checkout(path, comment=""):
        # type: (T_P4PATH, str) -> bool
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def revert(path):
        # type: (T_P4PATH) -> bool
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def move(path, new_path, change_description=None):
        # type: (T_P4PATH, T_P4PATH, str | None) -> bool
        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def get_existing_change_list(comment):
        # type: (str) -> dict | None
        """
        Get an existing change list with the given comment.
        """

        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def submit_change_list(comment):
        # type: (str) -> int | None
        """
        Submit an existing change list with the given comment.
        If no changelist exists with the given comment then
        raise `ChangeListNotFoundError`
        """

        raise NotImplementedError()

    @staticmethod
    @abc.abstractmethod
    def update_change_list_description(comment, new_comment):
        # type: (str, str) -> bool
        """
        Update the current change list's description to the given one.

        If the change list is not found it should raise: `ChangeListNotFoundError`.

        The implementation should also set `self.change_list_description = new_comment`
        """

        raise NotImplementedError()

    # Public Methods:
    def is_prefix_auto_generated(self, comment=""):
        # type: (str) -> bool
        comment = comment or self.change_list_description
        if not comment.startswith("["):
            return False

        description = comment.split("]")[-1]
        current_prefix = comment.replace(description, "")
        auto_prefix = self.change_list_description_prefix
        return current_prefix == auto_prefix
