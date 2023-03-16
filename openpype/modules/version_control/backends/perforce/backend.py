
import six

from . import api
from .. import abstract

if six.PY2:
    import pathlib2 as pathlib
else:
    import pathlib

_typing = False
if _typing:
    from typing import Any
    from typing import Sequence
del _typing


class VersionControlPerforce(abstract.VersionControl):
    @staticmethod
    def get_server_version(path):
        # type: (str | pathlib.Path) -> int | None | dict[str, int | None]
        result = api.get_current_server_revision(path)
        return result

    @staticmethod
    def get_local_version(path):
        # type: (pathlib.Path | str) -> int | None
        result = api.get_current_client_revision(path)
        return result

    @staticmethod
    def get_version_info(path):
        # type: (pathlib.Path | str) -> tuple[int | None, int | None]
        result = api.get_version_info(path)
        return result

    @staticmethod
    def is_latest_version(path):
        # type: (pathlib.Path | str) -> bool | None
        return api.is_latest(path)

    @staticmethod
    def is_checkedout(path):
        # type: (pathlib.Path | str) -> bool
        return api.is_checked_out(path)

    @staticmethod
    def checked_out_by(path, other_users_only=False):
        # type: (pathlib.Path | str, bool) -> list[str] | None
        return api.checked_out_by(path, other_users_only=other_users_only)

    @staticmethod
    def exists_on_server(path):
        # type: (pathlib.Path | str) -> bool
        if api.get_stat(path, ["-m 1"]) is None:
            return False

        return True

    @staticmethod
    def sync_latest_version(path):
        # type: (pathlib.Path | str) -> bool | None
        return api.get_latest(path)

    @staticmethod
    def sync_to_version(path, version):
        # type: (pathlib.Path | str, int) -> bool | None
        return api.get_revision(path, version)

    @staticmethod
    def add(path, comment=""):
        # type: (pathlib.Path | str, str) -> bool
        return api.add(path, change_description=comment)

    @staticmethod
    def add_to_change_list(path, comment):
        # type: (pathlib.Path | str, str) -> bool
        return api.add_to_change_list(path, comment)

    @staticmethod
    def checkout(path, comment=""):
        # type: (pathlib.Path | str, str) -> bool
        return api.checkout(path, change_description=comment)

    @staticmethod
    def revert(path):
        # type: (pathlib.Path | str) -> bool
        return api.revert(path)

    @staticmethod
    def move(path, new_path, change_description=None):
        # type: (pathlib.Path | str, pathlib.Path | str, str | None) -> bool | None
        return api.move(path, new_path, change_description=change_description)

    @staticmethod
    def get_existing_change_list(comment):
        # type: (str) -> dict[str, Any] | None
        return api.get_existing_change_list(comment)

    @staticmethod
    def get_files_in_folder_in_date_order(path, name_pattern=None, extensions=None):
        # type: (pathlib.Path | str, str | None, Sequence[str] | None) -> tuple[pathlib.Path | None]
        return tuple(
            (
                data.path for data in api.get_files_in_folder_in_date_order(
                    path, name_pattern=name_pattern, extensions=extensions
                ) or []
            )
        )

    @staticmethod
    def get_newest_file_in_folder(path, name_pattern=None, extensions=None):
        # type: (pathlib.Path | str, str | None, Sequence[str] | None) -> pathlib.Path | None
        result = api.get_newest_file_in_folder(
            path, name_pattern=name_pattern, extensions=extensions
        )
        if result is None:
            return

        return result.path

    @staticmethod
    def submit_change_list(comment):
        # type: (str) -> int | None
        return api.submit_change_list(comment)

    @staticmethod
    def update_change_list_description(comment, new_comment):
        # type: (str, str) -> bool
        return api.update_change_list_description(comment, new_comment)
