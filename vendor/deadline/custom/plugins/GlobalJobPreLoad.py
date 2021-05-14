# -*- coding: utf-8 -*-
import os
import tempfile
import time
import subprocess
import json
import platform
from Deadline.Scripting import RepositoryUtils, FileUtils


def inject_openpype_environment(deadlinePlugin):
    job = deadlinePlugin.GetJob()
    job = RepositoryUtils.GetJob(job.JobId, True)  # invalidates cache

    print("inject_openpype_environment start")
    try:
        exe_list = job.GetJobExtraInfoKeyValue("openpype_executables")
        openpype_app = FileUtils.SearchFileList(exe_list)
        if openpype_app == "":
            raise RuntimeError(
                "OpenPype executable was not found " +
                "in the semicolon separated list \"" + exe_list + "\". " +
                "The path to the render executable can be configured " +
                "from the Plugin Configuration in the Deadline Monitor.")

        # tempfile.TemporaryFile cannot be used because of locking
        export_url = os.path.join(tempfile.gettempdir(),
                                  time.strftime('%Y%m%d%H%M%S'),
                                  'env.json')  # add HHMMSS + delete later
        print("export_url {}".format(export_url))

        args = [
            openpype_app,
            'extractenvironments',
            export_url
        ]

        add_args = {}
        add_args['project'] = \
            job.GetJobEnvironmentKeyValue('AVALON_PROJECT')
        add_args['asset'] = job.GetJobEnvironmentKeyValue('AVALON_ASSET')
        add_args['task'] = job.GetJobEnvironmentKeyValue('AVALON_TASK')
        add_args['app'] = job.GetJobEnvironmentKeyValue('AVALON_APP_NAME')

        if all(add_args.values()):
            for key, value in add_args.items():
                args.append("--{}".format(key))
                args.append(value)
        else:
            msg = "Required env vars: AVALON_PROJECT, AVALON_ASSET, " + \
                  "AVALON_TASK, AVALON_APP_NAME"
            raise RuntimeError(msg)

        print("args::{}".format(args))

        exit_code = subprocess.call(args, shell=True)
        if exit_code != 0:
            raise RuntimeError("Publishing failed, check worker's log")

        with open(export_url) as fp:
            contents = json.load(fp)
            for key, value in contents.items():
                deadlinePlugin.SetProcessEnvironmentVariable(key, value)

        os.remove(export_url)

        print("inject_openpype_environment end")
    except Exception:
        import traceback
        print(traceback.format_exc())
        print("inject_openpype_environment failed")
        RepositoryUtils.FailJob(job)
        raise


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
    # PYPE should be here, not OPENPYPE - backward compatibility!!
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
    job = deadlinePlugin.GetJob()
    job = RepositoryUtils.GetJob(job.JobId, True)  # invalidates cache

    openpype_render_job = \
        job.GetJobEnvironmentKeyValue('OPENPYPE_RENDER_JOB') or '0'
    openpype_publish_job = \
        job.GetJobEnvironmentKeyValue('OPENPYPE_PUBLISH_JOB') or '0'

    if openpype_publish_job == '1' and openpype_render_job == '1':
        raise RuntimeError("Misconfiguration. Job couldn't be both " +
                           "render and publish.")

    if openpype_publish_job == '1':
        print("Publish job, skipping inject.")
        return
    elif openpype_render_job == '1':
        inject_openpype_environment(deadlinePlugin)
    else:
        pype(deadlinePlugin)  # backward compatibility with Pype2
