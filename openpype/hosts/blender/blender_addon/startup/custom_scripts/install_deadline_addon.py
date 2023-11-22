import sys
import os
import bpy
import addon_utils
import logging
import subprocess
from pathlib import Path


def execute():
    path = get_repository_path("submission/Blender/Client")
    if not path:
        logging.warning("Can't find Deadline submission repository for Blender. Abort process.")
        raise ImportError

    deadline_addon_file_name = _get_python_addon_file(path)
    deadline_addon_name = Path(deadline_addon_file_name).stem

    if _is_already_installed(deadline_addon_name):
        logging.info("Deadline addon is already installed")
    else:
        try:
            deadline_addon_path = os.path.join(path, deadline_addon_file_name)
        except StopIteration:
            logging.warning("Can't find Deadline submission addon for Blender. Abort process.")
            raise StopIteration

        bpy.ops.preferences.addon_install(
            overwrite=True,
            filepath=deadline_addon_path
        )
        deadline_addon_name = Path(deadline_addon_file_name).stem
        logging.info("Deadline addon has been correctly installed.")

    bpy.ops.preferences.addon_enable(module=deadline_addon_name)
    bpy.ops.wm.save_userpref()


def _get_python_addon_file(path):
    return next(
        iter(
            [
                file_name for file_name in os.listdir(path) if
                os.path.isfile(os.path.join(path, file_name)) and
                file_name.endswith('.py')
            ]
        )
    )


def _is_already_installed(deadline_addon_name):
    return deadline_addon_name in bpy.context.preferences.addons


def get_deadline_command():
    deadlineBin = ""
    try:
        deadlineBin = os.environ['DEADLINE_PATH']
    except KeyError:
        #if the error is a key error it means that DEADLINE_PATH is not set. however Deadline command may be in the PATH or on OSX it could be in the file /Users/Shared/Thinkbox/DEADLINE_PATH
        deadlineBin = "C:/Program Files/Thinkbox/Deadline10/bin/"
        pass

    # Determine if the installer is being run on OSX
    if sys.platform == "darwin":
        # On OSX, we look for the DEADLINE_PATH file if the environment variable does not exist.
        if deadlineBin == "" and  os.path.exists( "/Users/Shared/Thinkbox/DEADLINE_PATH" ):
            with open( "/Users/Shared/Thinkbox/DEADLINE_PATH" ) as f:
                deadlineBin = f.read().strip()

    deadlineCommand = os.path.join(deadlineBin, "deadlinecommand")

    return deadlineCommand


def get_repository_path(subdir = None):
    deadlineCommand = get_deadline_command()
    startupinfo = None

    args = [deadlineCommand, "-GetRepositoryPath "]
    if subdir != None and subdir != "":
        args.append(subdir)

    # Specifying PIPE for all handles to workaround a Python bug on Windows. The unused handles are then closed immediatley afterwards.
    proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, startupinfo=startupinfo)

    proc.stdin.close()
    proc.stderr.close()

    output = proc.stdout.read()

    path = output.decode("utf_8")
    path = path.replace("\r","").replace("\n","").replace("\\","/")

    return path

execute()
