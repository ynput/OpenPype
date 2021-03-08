import os
import sys
import json
import datetime
import platform
import getpass
import socket

import pype.version
from pype.settings.lib import get_local_settings
from .execute import get_pype_execute_args
from .local_settings import get_local_site_id


def get_pype_version():
    return pype.version.__version__


def get_pype_info():
    executable_args = get_pype_execute_args()
    if len(executable_args) == 1:
        version_type = "build"
    else:
        version_type = "code"

    return {
        "version": get_pype_version(),
        "version_type": version_type,
        "executable": executable_args[-1],
        "pype_root": os.environ["PYPE_ROOT"],
        "mongo_url": os.environ["PYPE_MONGO"]
    }


def get_workstation_info():
    host_name = socket.gethostname()
    try:
        host_ip = socket.gethostbyname(host_name)
    except socket.gaierror:
        host_ip = "127.0.0.1"

    return {
        "hostname": host_name,
        "hostip": host_ip,
        "username": getpass.getuser(),
        "system_name": platform.system(),
        "local_id": get_local_site_id()
    }


def get_all_data():
    return {
        "pype": get_pype_info(),
        "workstation": get_workstation_info(),
        "env": os.environ.copy(),
        "local_settings": get_local_settings()
    }


def extract_pype_info_to_file(dirpath):
    filename = "{}_{}_{}.json".format(
        get_pype_version(),
        get_local_site_id(),
        datetime.datetime.now().strftime("%y%m%d%H%M%S")
    )
    filepath = os.path.join(dirpath, filename)
    data = get_all_data()
    if not os.path.exists(dirpath):
        os.makedirs(dirpath)

    with open(filepath, "w") as file_stream:
        json.dump(data, file_stream)
    return filepath
