# -*- coding: utf-8 -*-
import os
import tempfile
from datetime import datetime
import subprocess
import json
import platform
import uuid
from Deadline.Scripting import RepositoryUtils, FileUtils


def get_openpype_executable():
    """Return OpenPype Executable from Event Plug-in Settings"""
    config = RepositoryUtils.GetPluginConfig("OpenPype")
    return config.GetConfigEntryWithDefault("OpenPypeExecutable", "")


def inject_openpype_environment(deadlinePlugin):
    """ Pull env vars from OpenPype and push them to rendering process.

        Used for correct paths, configuration from OpenPype etc.
    """
    job = deadlinePlugin.GetJob()

    print(">>> Injecting OpenPype environments ...")
    try:
        print(">>> Getting OpenPype executable ...")
        exe_list = get_openpype_executable()
        openpype_app = FileUtils.SearchFileList(exe_list)
        if openpype_app == "":
            raise RuntimeError(
                "OpenPype executable was not found " +
                "in the semicolon separated list \"" + exe_list + "\". " +
                "The path to the render executable can be configured " +
                "from the Plugin Configuration in the Deadline Monitor.")

        print("--- OpenPype executable: {}".format(openpype_app))

        # tempfile.TemporaryFile cannot be used because of locking
        temp_file_name = "{}_{}.json".format(
            datetime.utcnow().strftime('%Y%m%d%H%M%S%f'),
            str(uuid.uuid1())
        )
        export_url = os.path.join(tempfile.gettempdir(), temp_file_name)
        print(">>> Temporary path: {}".format(export_url))

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
        add_args["envgroup"] = "farm"

        if all(add_args.values()):
            for key, value in add_args.items():
                args.append("--{}".format(key))
                args.append(value)
        else:
            msg = "Required env vars: AVALON_PROJECT, AVALON_ASSET, " + \
                  "AVALON_TASK, AVALON_APP_NAME"
            raise RuntimeError(msg)

        if not os.environ.get("OPENPYPE_MONGO"):
            print(">>> Missing OPENPYPE_MONGO env var, process won't work")

        env = os.environ
        env["OPENPYPE_HEADLESS_MODE"] = "1"
        env["AVALON_TIMEOUT"] = "5000"

        print(">>> Executing: {}".format(args))
        std_output = subprocess.check_output(args,
                                             cwd=os.path.dirname(openpype_app),
                                             env=env)
        print(">>> Process result {}".format(std_output))

        print(">>> Loading file ...")
        with open(export_url) as fp:
            contents = json.load(fp)
            for key, value in contents.items():
                deadlinePlugin.SetProcessEnvironmentVariable(key, value)

        print(">>> Removing temporary file")
        os.remove(export_url)

        print(">> Injection end.")
    except Exception as e:
        if hasattr(e, "output"):
            print(">>> Exception {}".format(e.output))
        import traceback
        print(traceback.format_exc())
        print("!!! Injection failed.")
        RepositoryUtils.FailJob(job)
        raise


def inject_render_job_id(deadlinePlugin):
    """Inject dependency ids to publish process as env var for validation."""
    print(">>> Injecting render job id ...")
    job = deadlinePlugin.GetJob()

    dependency_ids = job.JobDependencyIDs
    print(">>> Dependency IDs: {}".format(dependency_ids))
    render_job_ids = ",".join(dependency_ids)

    deadlinePlugin.SetProcessEnvironmentVariable("RENDER_JOB_IDS",
                                                 render_job_ids)
    print(">>> Injection end.")


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
    print(">>> Getting job ...")
    job = deadlinePlugin.GetJob()
    # PYPE should be here, not OPENPYPE - backward compatibility!!
    pype_metadata = job.GetJobEnvironmentKeyValue("PYPE_METADATA_FILE")
    pype_python = job.GetJobEnvironmentKeyValue("PYPE_PYTHON_EXE")
    print(">>> Having backward compatible env vars {}/{}".format(pype_metadata,
                                                                 pype_python))
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
    print("*** GlobalJobPreload start ...")
    print(">>> Getting job ...")
    job = deadlinePlugin.GetJob()

    openpype_render_job = \
        job.GetJobEnvironmentKeyValue('OPENPYPE_RENDER_JOB') or '0'
    openpype_publish_job = \
        job.GetJobEnvironmentKeyValue('OPENPYPE_PUBLISH_JOB') or '0'

    print("--- Job type - render {}".format(openpype_render_job))
    print("--- Job type - publish {}".format(openpype_publish_job))
    if openpype_publish_job == '1' and openpype_render_job == '1':
        raise RuntimeError("Misconfiguration. Job couldn't be both " +
                           "render and publish.")

    if openpype_publish_job == '1':
        inject_render_job_id(deadlinePlugin)
    elif openpype_render_job == '1':
        inject_openpype_environment(deadlinePlugin)
    else:
        pype(deadlinePlugin)  # backward compatibility with Pype2
