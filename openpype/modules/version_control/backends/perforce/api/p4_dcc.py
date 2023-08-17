from __future__ import annotations

import os
import pathlib
import tool_settings
import qt_sm.dialogs as sm_dialogs
import Qt.QtCore as QtCore  # type: ignore

from .. import api
from . import p4_errors

_typing = False
if _typing:
    from typing import Union

    _PathTypes = Union[str, pathlib.Path, pathlib.Path]
del _typing


def on_pre_open(file_path: _PathTypes, tool_name: str) -> bool:
    """
    Check if the given file exists on the server and if it is latest,
    offering the appropriate prompts to the user during the process.

    Arguments:
    ---------
        - `file_path`: The path to check.
        - `tool_name`: The name of the tool to run this operation for.
            This allows the correct settings to be queried.

    Returns:
    --------
        `True` if the file is exists on the server and is latest, `False` if not.
    """

    _file_path = pathlib.Path(file_path)
    get_latest_on_load_behaviour = tool_settings.get_setting(
        tool_name, "get_latest_on_load_behaviour", default_setting_value="Prompt"
    )
    if api.is_offline:
        if get_latest_on_load_behaviour == "Prompt":
            sm_dialogs.show_message_box(
                (
                    "Perforce is offline, cannot get latest if local file is out of sync!\n"
                    "!!! Work with caution !!!"
                )
            )

        return False

    exists_on_server = _file_path.p4.exists_on_server
    if not exists_on_server:
        return False

    file_path_short = f"...{str(_file_path).split('Art')[-1]}"
    get_latest_on_load = tool_settings.get_setting(
        tool_name, "get_latest_on_load", default_setting_value=True
    )
    warn_if_checked_out: bool = tool_settings.get_setting(
        tool_name, "load_warn_checked_out", default_setting_value=True
    )
    if warn_if_checked_out:
        _checked_out_by = _file_path.p4.checked_out_by
        workspaces = set(api.get_workspaces())
        checked_out_by = [
            f"'{user}' in workspace: '{workspace}'" for user, workspace in _checked_out_by if workspace not in workspaces
        ] if _checked_out_by else []
        if checked_out_by:
            message_text = f"This file:\n\n{file_path_short}\n\nIs checked out by the following users:\n"
            for user in checked_out_by:
                message_text = f"{message_text}\n - {user}"

            sm_dialogs.show_message_box(message_text, title="Just To Let You Know")

    is_latest = _file_path.p4.is_latest
    if not get_latest_on_load:
        return True if is_latest is None else is_latest

    prompt_pre_open = get_latest_on_load_behaviour == "Prompt"
    if is_latest is False and prompt_pre_open:
        get_latest_on_load = sm_dialogs.show_query_box(
            f"Would you like to get latest on this file:\n\n{file_path_short}"
        )

    if get_latest_on_load and is_latest is False:
        _file_path.p4.get_latest()
        print(f"Getting latest on this file:\n - {_file_path}")

    if (not is_latest) and (not get_latest_on_load):
        print(f"This file is not the latest version:\n - {_file_path}")
        return False

    return True


def on_post_open(file_path: _PathTypes, tool_name: str) -> None:
    """
    Check if the given file exists on the server.

    This is called after a file has loaded.
    If the file is not on p4, add it automatically, prompt the
    user if they want to add it or ignore it all together,
    depending on the users p4 settings.

    Arguments:
    ---------
        - `file_path`: The path to check.
        - `tool_name`: The name of the tool to run this operation for.
            This allows the correct settings to be queried.
    """

    file_path = pathlib.Path(file_path)
    add_on_load = tool_settings.get_setting(tool_name, "add_on_load", default_setting_value=True)
    if not add_on_load:
        return

    if api.is_offline:
        if add_on_load:
            sm_dialogs.show_message_box(
                "Perforce is offline, add command is being added to the offline cache!"
            )
        file_path.p4.add()
        return

    exists_on_server = file_path.p4.exists_on_server
    if exists_on_server:
        return

    add_on_load_behaviour = tool_settings.get_setting(
        tool_name, "add_on_load_behaviour", default_setting_value="Prompt"
    )
    file_path_short = f"...{str(file_path).split('Art')[-1]}"
    prompt_post_save = add_on_load_behaviour == "Prompt"
    add_file = True
    if (not exists_on_server) and prompt_post_save:
        add_file = sm_dialogs.show_query_box(
            f"Would you like to add this file to p4:\n\n{file_path_short}"
        )

    if not add_file:
        return

    if file_path.p4.add():
        print(f"Added file:\n - {file_path}")


def on_pre_save(file_path: _PathTypes, tool_name: str) -> bool:
    """
    Check if the given file exists on the server and if it is latest
    and checking it out if so, offering the appropriate prompts
    to the user during the process.

    Arguments:
    ---------
        - `file_path`: The path to check.
        - `tool_name`: The name of the tool to run this operation for.
            This allows the correct settings to be queried.

    Returns:
    --------
        `True` if the file is exists on the server, is latest
            and has been checked out, `False` if not.
    """

    file_path = pathlib.Path(file_path)
    file_path_short = f"...{str(file_path).split('Art')[-1]}"
    checkout_on_save = tool_settings.get_setting(
        tool_name, "checkout_on_save", default_setting_value=True
    )

    checkout_on_save_behaviour = tool_settings.get_setting(
        tool_name, "checkout_on_save_behaviour", default_setting_value="Automatically"
    )
    prompt_pre_save = checkout_on_save_behaviour == "Prompt"

    if api.is_offline and checkout_on_save:
        if os.access(file_path, os.R_OK, follow_symlinks=True):
            return True

        checkout_file = True
        if prompt_pre_save:
            checkout_file = sm_dialogs.show_query_box(
                f"Would you like to check this file out:\n\n{file_path_short}"
            )

        if not checkout_file:
            return False

        sm_dialogs.show_message_box(
            "Peforce is offline, check out command is being added to the offline cache!"
        )
        file_path.p4.checkout()
        return True

    if not checkout_on_save:
        return False

    if file_path.is_dir():
        raise AttributeError("Not sure how this has happened, but you are trying to check a folder!")

    # @sharkmob-shea.richardson
    # We get a single stat and query the values of the dict
    # rather than running separate functions on the path.p4 interface.
    # This will reduce the number of calls to the server by a fair amount:
    stat = file_path.p4.get_stat()
    exists_on_server = bool(stat)
    if not exists_on_server:
        return False

    def _is_file_latest(data):
        # type: (dict) -> bool
        valid_states = {"add", "move/add", "edit"}
        if "action" in data and data["action"] in valid_states:
            return True
        if "headRev" not in data:
            return False
        if "haveRev" not in data:
            return False

        return data["headRev"] == data["haveRev"]

    is_latest = _is_file_latest(stat)
    if not is_latest:
        continue_process = sm_dialogs.show_query_box(
            (
                f"This file is not the latest version:\n\n{file_path_short}\n\n"
                "Continuing to get latest and then saving will override other peoples work.\n"
                "Are you sure you would like to override other peoples work?"
            )
        )
        if not continue_process:
            return False

        is_latest = file_path.p4.get_latest()

    if not is_latest:
        sm_dialogs.show_message_box("File is not latest - cannot save!")
        return False

    checkout_file = True
    is_checked_out = False
    if "otherAction" in stat:
        is_checked_out = "edit" in stat["otherAction"]

    elif "action" in stat:
        action = stat["action"]
        is_checked_out = "edit" in action or "add" in action

    warn_if_checked_out: bool = tool_settings.get_setting(
        tool_name, "save_warn_checked_out", default_setting_value=True
    )
    if is_checked_out:
        _checked_out_by = file_path.p4.checked_out_by
        workspaces = set(p4.get_workspaces())
        checked_out_by = [
            f"'{user}' in workspace: '{workspace}'" for user, workspace in _checked_out_by if workspace not in workspaces
        ] if _checked_out_by else []
        if checked_out_by:
            if "headType" in stat and "+l" in stat["headType"]:
                checked_out_by_str = "\n - ".join(checked_out_by)
                sm_dialogs.show_message_box(
                    (
                        f"This file is exclusively checked out by:\n\n - {checked_out_by_str}\n\n"
                        "This means it cannot be checked out nor saved locally!"
                    )
                )
                return False

            if warn_if_checked_out:
                    message_text = f"This file:\n\n{file_path_short}\n\nIs checked out by the following users:\n"
                    for user in checked_out_by:
                        message_text = f"{message_text}\n - {user}"

                    message_text = (
                        f"{message_text}\n\nChecking out and saving can result in lost work!"
                        "\nAre you sure you would you like to do this?"
                    )

                    checkout_file = sm_dialogs.show_query_box(message_text)
                    if not checkout_file:
                        return False

                    if checkout_file:
                        sm_dialogs.show_message_box(
                            (
                                f"Simultaneous file check outs are risky business!\n\n"
                                "Be cautious so as to avoid loss of work!"
                            )
                        )

    if prompt_pre_save and not is_checked_out:
        checkout_file = sm_dialogs.show_query_box(
            f"Would you like to check this file out:\n\n{file_path_short}"
        )

    if checkout_file and not is_checked_out:
        try:
            if file_path.p4.checkout():
                print(f"Checked out file:\n - {file_path}")
                return True
        except p4_errors.P4ExclusiveCheckoutError as error:
            sm_dialogs.show_query_box(str(error))

    return False


def on_post_save(file_path: _PathTypes, tool_name: str) -> None:
    """
    Check if the given path exists on perforce and adds it if not,
    offering the appropriate prompts to the user during the process.


    Arguments:
    ---------
        - `file_path`: The path to check.
        - `tool_name`: The name of the tool to run this operation for.
            This allows the correct settings to be queried.

    """
    file_path = pathlib.Path(file_path)
    add_on_save = tool_settings.get_setting(tool_name, "add_on_save", default_setting_value=True)
    if not add_on_save:
        return

    if api.is_offline and add_on_save:
        sm_dialogs.show_message_box(
            "Peforce is offline, add command is being added to the offline cache!"
        )
        file_path.p4.add()
        return

    exists_on_server = file_path.p4.exists_on_server
    if exists_on_server:
        return

    add_on_save_behaviour = tool_settings.get_setting(
        tool_name, "add_on_save_behaviour", default_setting_value="Automatically"
    )
    prompt_post_save = add_on_save_behaviour == "Prompt"
    add_file = True
    file_path_short = f"...{str(file_path).split('Art')[-1]}"
    if (not exists_on_server) and prompt_post_save:
        add_file = sm_dialogs.show_query_box(
            f"Would you like to add this file to p4:\n\n{file_path_short}"
        )

    if not add_file:
        return

    if file_path.p4.add():
        print(f"Added file:\n - {file_path}")


_has_disconnected = False

@QtCore.Slot()
def _on_p4_connect():
    global _has_disconnected
    if _has_disconnected:
        sm_dialogs.show_message_box("Perforce has re-connected!", greeting="Good news")


@QtCore.Slot()
def _on_p4_disconnect():
    global _has_disconnected
    _has_disconnected = True
    sm_dialogs.show_message_box("Perforce appears to have died!", greeting="Sad news")


_slots_connected = False


def disconnect_slots():
    global _slots_connected
    if not _slots_connected:
        return
    api._get_connection_manager()._signaller.connected.disconnect(_on_p4_connect)
    api._get_connection_manager()._signaller.disconnected.disconnect(_on_p4_disconnect)
    _slots_connected = False


def connect_slots():
    global _slots_connected
    disconnect_slots()
    api._get_connection_manager()._signaller.connected.connect(_on_p4_connect)
    api._get_connection_manager()._signaller.disconnected.connect(_on_p4_disconnect)
    _slots_connected = True



if __name__ in ("builtins", "__main__"):

    path = pathlib.Path(r"C:\p4ws\squid\Source\Art\Animation\_StagedAssets\Weapon\Gun\AK47\G_AK47.fbx")
    on_pre_open(path, "p4_mobu")
