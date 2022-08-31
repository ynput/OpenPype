import os
import json
from uuid import uuid4
from openpype.lib.pype_info import get_workstation_info


def _read_lock_file(lock_filepath):
    with open(lock_filepath, "r") as stream:
        data = json.load(stream)
    return data


def _get_lock_file(filepath):
    return filepath + ".lock"


def is_workfile_locked(filepath):
    lock_filepath = _get_lock_file(filepath)
    if not os.path.exists(lock_filepath):
        return False
    return True


def is_workfile_locked_for_current_process(filepath):
    if not is_workfile_locked():
        return False

    lock_filepath = _get_lock_file(filepath)
    process_id = os.environ["OPENPYPE_PROCESS_ID"]
    data = _read_lock_file(lock_filepath)
    return data["process_id"] == process_id


def delete_workfile_lock(filepath):
    lock_filepath = _get_lock_file(filepath)
    if not os.path.exists(lock_filepath):
        return

    if is_workfile_locked_for_current_process(filepath):
        os.remove(filepath)


def create_workfile_lock(filepath):
    lock_filepath = _get_lock_file(filepath)
    process_id = os.environ.get("OPENPYPE_PROCESS_ID")
    if not process_id:
        process_id = str(uuid4())
        os.environ["OPENPYPE_PROCESS_ID"] = process_id
    info = get_workstation_info()
    info["process_id"] = process_id
    with open(lock_filepath, "w") as stream:
        json.dump(info, stream)


def get_username(filepath):
    lock_filepath = _get_lock_file(filepath)
    with open(lock_filepath, "r") as stream:
        data = json.load(stream)
    username = data["username"]
    return username


def remove_workfile_lock(filepath):
    lock_filepath = _get_lock_file(filepath)
    if not os.path.exists(lock_filepath):
        return
    return os.remove(lock_filepath)

