# -*- coding: utf-8 -*-
"""Remap pype path and PYPE_METADATA_PATH."""
import platform
from Deadline.Scripting import RepositoryUtils


def pype_command_line(executable, arguments, workingDirectory):
    """Remap paths in comand line argument string.

    Using Deadline rempper it will remap all path found in command-line.

    Args:
        executable (str): path to executable
        arguments (str): arguments passed to executable
        workingDirectory (str): working directory path

    Returns:
        Tuple(executable, arguments, workingDirectory)

    """
    print("-" * 40)
    print("executable: {}".format(executable))
    print("arguments: {}".format(arguments))
    print("workingDirectory: {}".format(workingDirectory))
    print("-" * 40)
    print("Remapping arguments ...")
    arguments = RepositoryUtils.CheckPathMapping(arguments)
    print("* {}".format(arguments))
    print("-" * 40)
    return executable, arguments, workingDirectory


def pype(deadlinePlugin):
    """Remaps `PYPE_METADATA_FILE` and `PYPE_PYTHON_EXE` environment vars.

    `PYPE_METADATA_FILE` is used on farm to point to rendered data. This path
    originates on platform from which this job was published. To be able to
    publish on different platform, this path needs to be remapped.

    `PYPE_PYTHON_EXE` can be used to specify custom location of python
    interpreter to use for Pype. This is remappeda also if present even
    though it probably doesn't make much sense.

    Arguments:
        deadlinePlugin: Deadline job plugin passed by Deadline

    """
    job = deadlinePlugin.GetJob()
    pype_metadata = job.GetJobEnvironmentKeyValue("PYPE_METADATA_FILE")
    pype_python = job.GetJobEnvironmentKeyValue("PYPE_PYTHON_EXE")
    # test if it is pype publish job.
    if pype_metadata:
        pype_metadata = RepositoryUtils.CheckPathMapping(pype_metadata)
        if platform.system().lower() == "linux":
            pype_metadata = pype_metadata.replace("\\", "/")

        print("- remapping PYPE_METADATA_FILE: {}".format(pype_metadata))
        job.SetJobEnvironmentKeyValue("PYPE_METADATA_FILE", pype_metadata)
        deadlinePlugin.SetProcessEnvironmentVariable(
            "PYPE_METADATA_FILE", pype_metadata)

    if pype_python:
        pype_python = RepositoryUtils.CheckPathMapping(pype_python)
        if platform.system().lower() == "linux":
            pype_python = pype_python.replace("\\", "/")

        print("- remapping PYPE_PYTHON_EXE: {}".format(pype_python))
        job.SetJobEnvironmentKeyValue("PYPE_PYTHON_EXE", pype_python)
        deadlinePlugin.SetProcessEnvironmentVariable(
            "PYPE_PYTHON_EXE", pype_python)

    deadlinePlugin.ModifyCommandLineCallback += pype_command_line


def __main__(deadlinePlugin):
    pype(deadlinePlugin)
