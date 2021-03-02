# -*- coding: utf-8 -*-
import os
import tempfile
import time
import subprocess
import json
from Deadline.Scripting import RepositoryUtils, FileUtils


def inject_pype_environment(deadlinePlugin):
    job = deadlinePlugin.GetJob()
    job = RepositoryUtils.GetJob(job.JobId, True)  # invalidates cache

    pype_render_job = job.GetJobEnvironmentKeyValue('PYPE_RENDER_JOB') \
        or '0'
    pype_publish_job = job.GetJobEnvironmentKeyValue('PYPE_PUBLISH_JOB') \
        or '0'

    if pype_publish_job == '1' and pype_render_job == '1':
        raise RuntimeError("Misconfiguration. Job couldn't be both " +
                           "render and publish.")

    if pype_publish_job == '1':
        print("Publish job, skipping inject.")
        return
    elif pype_render_job == '0':
        # not pype triggered job
        return

    print("inject_pype_environment start")
    try:
        exe_list = job.GetJobExtraInfoKeyValue("pype_executables")
        pype_app = FileUtils.SearchFileList(exe_list)
        if pype_app == "":
            raise RuntimeError(
                "Pype executable was not found " +
                "in the semicolon separated list \"" + exe_list + "\". " +
                "The path to the render executable can be configured " +
                "from the Plugin Configuration in the Deadline Monitor.")

        # tempfile.TemporaryFile cannot be used because of locking
        export_url = os.path.join(tempfile.gettempdir(),
                                  time.strftime('%Y%m%d%H%M%S'),
                                  'env.json')  # add HHMMSS + delete later
        print("export_url {}".format(export_url))

        args = [
            pype_app,
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
                deadlinePlugin.SetEnvironmentVariable(key, value)

        os.remove(export_url)

        print("inject_pype_environment end")
    except Exception:
        import traceback
        print(traceback.format_exc())
        print("inject_pype_environment failed")
        RepositoryUtils.FailJob(job)
        raise


def __main__(deadlinePlugin):
    inject_pype_environment(deadlinePlugin)
