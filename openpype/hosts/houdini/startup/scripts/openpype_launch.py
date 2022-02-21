import os
import sys
import avalon.api
from openpype.hosts.houdini import api
import openpype.hosts.houdini.api.workio

import hou


def is_workfile(path):
    if not path:
        return

    if not os.path.exists(path):
        return False

    _, ext = os.path.splitext(path)
    if ext in openpype.hosts.houdini.api.workio.file_extensions():
        return True


def main():
    print("Installing OpenPype ...")
    avalon.api.install(api)

    args = sys.argv
    if args and is_workfile(args[-1]):
        # If the last argument is a Houdini file open it directly
        workfile_path = args[-1].replace("\\", "/")
        print("Opening workfile on launch: {}".format(workfile_path))

        # We don't use `workio.open_file` because we want to explicitly ignore
        # load warnings. Otherwise Houdini will fail to start if a scene load
        # produces e.g. errors on missing plug-ins
        hou.hipFile.load(workfile_path,
                         suppress_save_prompt=True,
                         ignore_load_warnings=True)


main()
