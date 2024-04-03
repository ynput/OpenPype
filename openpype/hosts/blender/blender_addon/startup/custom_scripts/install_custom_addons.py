import sys
import os
import bpy
import argparse
import logging
import subprocess
from pathlib import Path


def execute():
    blender_addons_folder_path = get_addons_folder_path()
    install_deadline_addon(blender_addons_folder_path)
    enable_user_addons(blender_addons_folder_path)
    bpy.ops.wm.save_userpref()


def install_deadline_addon(blender_addons_folder_path):
    path = get_repository_path("submission/Blender/Client")
    if not path:
        logging.warning("Can't find Deadline submission repository for Blender. Abort process.")
        return

    deadline_addon_file_name = get_python_addon_file(path)
    deadline_addon_name = Path(deadline_addon_file_name).stem

    if _is_already_installed(deadline_addon_name, blender_addons_folder_path):
        logging.info("Deadline addon is already installed")
        return

    try:
        deadline_addon_path = os.path.join(path, deadline_addon_file_name)
    except StopIteration:
        logging.warning("Can't find Deadline submission addon for Blender. Abort process.")
        return

    bpy.ops.preferences.addon_install(
        overwrite=True,
        filepath=deadline_addon_path
    )
    deadline_addon_name = Path(deadline_addon_file_name).stem
    logging.info("Deadline addon has been correctly installed.")


def get_python_addon_file(path):
    return next(iter(_list_python_files_in_dir(path)))


def get_python_addons_files(path):
    return _list_python_files_in_dir(path)


def _list_python_files_in_dir(path):
    return [
        file_name for file_name in os.listdir(path) if
        os.path.isfile(os.path.join(path, file_name)) and
        file_name.endswith('.py')
    ]


def _is_already_installed(deadline_addon_name, blender_addons_folder_path):
    try:
        return next(
            iter(
                deadline_addon_name in file \
                for file in os.listdir(blender_addons_folder_path)
            )
        )
    except FileNotFoundError or StopIteration:
        return False


def get_addons_folder_path():
    parser = argparse.ArgumentParser()
    parser.add_argument("--blender-addons-folder", help="Blender installed addons folder path")
    args, _ = parser.parse_known_args(
        sys.argv[sys.argv.index("--") + 1 :]
    )
    return args.blender_addons_folder


def enable_user_addons(blender_addons_folder_path):
    for addon in get_python_addons_files(blender_addons_folder_path):
        bpy.ops.preferences.addon_enable(module=Path(addon).stem)


def get_deadline_command():
    deadlineBin = ""
    try:
        deadlineBin = os.environ['DEADLINE_PATH']
    except KeyError:
        #if the error is a key error it means that DEADLINE_PATH is not set. however Deadline command may be in the PATH or on OSX it could be in the file /Users/Shared/Thinkbox/DEADLINE_PATH
        deadlineBin = "C:/Program Files/Thinkbox/Deadline10/bin/"

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
    if subdir:
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
