import os
import json
import glob
from datetime import datetime
import tempfile
import subprocess
import uuid

logs = []


class InjectEnvironment:
    """Creates rrEnv file and adds it to the rendered job.

    RR evnList has limitation on 2000 characters, which might not be enough.
    This script should be triggered by render jobs that were published from
    Ayon, it uses .json metadata to parse context and required Ayon launch
    environments to generate environment variable file for particular context.

    This file is converted into rrEnv file and added to the job to be picked up
    by RR.

    Expected set environments on RR worker:
    - AYON_SERVER_URL
    - AYON_API_KEY - API key to Ayon server, most likely from service account
    - AYON_EXECUTABLE_PATH - locally accessible path for `ayon_console`
    (could be removed if it would be possible to have it in renderApps config
    and to be accessible from there as there it is required for publish jobs).

    Ayon submission job must be adding this line to .xml submission file:
    <SubmitterParameter>OSperjob_ayon_inject_envvar=1~1</SubmitterParameter>

    Scripts logs into folder with metadata json - could be removed if there
    is a way how to log into RR output.

    """

    def __init__(self):
        self.meta_dir = None

    def inject(self):
        logs.append("InjectEnvironment starting")
        meta_dir = self._get_metadata_dir()

        metadata = self._get_metadata(meta_dir)
        if not metadata:
            logs.append("No metadata json found {}".format(meta_dir))
            return
        self.meta_dir = meta_dir

        if not self._is_required_environment():
            return

        context = self._get_context(metadata)
        logs.append("context {}".format(context))

        executable = self._get_executable()
        logs.append("executable {}".format(executable))

        extracted_env = self._extract_environments(executable, context,
                                                   metadata)

        rrEnv_path = self._create_rrEnv(meta_dir, extracted_env)

        self._set_rrEnv_to_job(rrEnv_path)
        logs.append("InjectEnvironment ending")

    def _get_metadata_dir(self):
        job = rr.getJob()
        image_dir = job.imageDir
        logs.append(f"_get_metadata_dir::{image_dir}")

        return image_dir

    def _get_metadata(self, meta_dir):
        search_frm = "{}{}*_metadata.json".format(meta_dir, os.path.sep)
        metadata_files = glob.glob(search_frm)
        if not metadata_files:
            return {}

        logs.append(f"_get_metadata::{metadata_files[0]}")
        with open(metadata_files[0]) as json_file:
            return json.load(json_file)

    def _is_required_environment(self):
        if (not os.environ.get("AYON_API_KEY") or
                not os.path.exists(os.environ.get("AYON_EXECUTABLE_PATH", ""))
        ):
            msg = ("AYON_API_KEY and AYON_EXECUTABLE_PATHenv var must be set "
                   "for Ayon jobs!")
            logs.append(msg)
            return False
        return True

    def _get_context(self, metadata_content):
        envs = self._get_job_environments(metadata_content)

        return {"project": envs["AVALON_PROJECT"],
                "asset": envs["AVALON_ASSET"],
                "task": envs["AVALON_TASK"],
                "app": envs["AVALON_APP_NAME"],
                "envgroup": "farm"}

    def _get_job_environments(self, metadata_content):
        """Gets environments set on job.

        It seems that it is not possible to query "rrEnvList" on job directly,
        it must be parsed from .json document.
        """
        job = metadata_content["job"]
        env_list = job["rrEnvList"]
        envs = {}
        for env in env_list.split("~~~"):
            key, value = env.split("=")
            envs[key] = value
        return envs

    def _get_executable(self):
        # rr_python_utils.cache.get_rr_bin_folder()  # TODO maybe useful
        return os.environ["AYON_EXECUTABLE_PATH"]

    def _extract_environments(self, executable, context, metadata_content):
        # tempfile.TemporaryFile cannot be used because of locking
        export_url = self._get_export_url()

        args = [
            executable,
            "--headless",
            "extractenvironments",
            export_url
        ]

        if all(context.values()):
            for key, value in context.items():
                args.extend(["--{}".format(key), value])

        environments = self._get_launch_environments(metadata_content)

        logs.append("Running:: {}".format(args))
        proc = subprocess.Popen(args, env=environments,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        output, error = proc.communicate()

        if not os.path.exists(export_url):
            raise RuntimeError("Extract failed with {}".format(error))

        with open(export_url) as json_file:
            return json.load(json_file)

    def _get_launch_environments(self, metadata_content):
        """ Enhances environemnt with required for Ayon to be launched."""
        job_envs = self._get_job_environments(metadata_content)
        ayon_environment = {
            "AYON_SERVER_URL": os.environ["AYON_SERVER_URL"],
            "AYON_API_KEY": os.environ["AYON_API_KEY"],
            "AYON_BUNDLE_NAME": job_envs["AYON_BUNDLE_NAME"],
        }

        environment = os.environ.copy()
        environment.update(ayon_environment)
        return environment

    def _get_export_url(self):
        temp_file_name = "{}_{}.json".format(
            datetime.utcnow().strftime('%Y%m%d%H%M%S%f'),
            str(uuid.uuid1())
        )
        export_url = os.path.join(tempfile.gettempdir(), temp_file_name)
        return export_url

    def _create_rrEnv(self, meta_dir, extracted_env):
        filter_out = os.environ.get("AYON_FILTER_ENVIRONMENTS")
        filter_envs = set()
        if filter_out:
            filter_envs = set(filter_out.split(";"))

        lines = []
        for key, value in extracted_env.items():
            if key in filter_envs:
                continue

            line = f"{key} = {value}"
            lines.append(line)

        rrenv_path = os.path.join(meta_dir, "rrEnv.rrEnv")
        with open(rrenv_path, "w") as fp:
            fp.writelines(s + '\n' for s in lines)

        return rrenv_path

    def _set_rrEnv_to_job(self, rrEnv_path):
        logs.append(f"_set_rrEnv_to_job::{rrEnv_path}")
        job = rr.getJob()

        job.customDataSet_Str("rrEnvFile", rrEnv_path)
        rr.setJob(job)


if __name__ == "__main__":

    try:
        injector = InjectEnvironment()
        injector.inject()
    except Exception as exp:
        logs.append(f"Error happened::{str(exp)}")

    log_path = os.path.join(injector.meta_dir, "log.txt")
    with open(log_path, "w") as fp:
        fp.writelines(s + '\n' for s in logs)
