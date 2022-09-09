import os
import json
from uuid import uuid4
from openpype.lib import Logger, filter_profiles
from openpype.lib.pype_info import get_workstation_info
from openpype.settings import get_project_settings


def _read_lock_file(lock_filepath):
    if not os.path.exists(lock_filepath):
        log = Logger.get_logger("_read_lock_file")
        log.debug("lock file is not created or readable as expected!")
    with open(lock_filepath, "r") as stream:
        data = json.load(stream)
    return data


def _get_lock_file(filepath):
    return filepath + ".oplock"


def is_workfile_locked(filepath):
    lock_filepath = _get_lock_file(filepath)
    if not os.path.exists(lock_filepath):
        return False
    return True


def is_workfile_locked_for_current_process(filepath):
    if not is_workfile_locked(filepath):
        return False

    lock_filepath = _get_lock_file(filepath)
    data = _read_lock_file(lock_filepath)
    return data["process_id"] == _get_process_id()


def delete_workfile_lock(filepath):
    lock_filepath = _get_lock_file(filepath)
    if os.path.exists(lock_filepath):
        os.remove(lock_filepath)


def create_workfile_lock(filepath):
    lock_filepath = _get_lock_file(filepath)
    info = get_workstation_info()
    info["process_id"] = _get_process_id()
    with open(lock_filepath, "w") as stream:
        json.dump(info, stream)


def get_user_from_lock(filepath):
    lock_filepath = _get_lock_file(filepath)
    if not os.path.exists(lock_filepath):
        return
    data = _read_lock_file(lock_filepath)
    username = data["username"]
    return username


def remove_workfile_lock(filepath):
    if is_workfile_locked_for_current_process(filepath):
        delete_workfile_lock(filepath)


def _get_process_id():
    process_id = os.environ.get("OPENPYPE_PROCESS_ID")
    if not process_id:
        process_id = str(uuid4())
        os.environ["OPENPYPE_PROCESS_ID"] = process_id
    return process_id


def is_workfile_lock_enabled(host_name, project_name, project_setting=None):
    if project_setting is None:
        project_setting = get_project_settings(project_name)
    workfile_lock_profiles = (
        project_setting
        ["global"]
        ["tools"]
        ["Workfiles"]
        ["workfile_lock_profiles"])
    profile = filter_profiles(workfile_lock_profiles,{"host_name": host_name})
    if not profile:
        return False
    return profile["enabled"]
