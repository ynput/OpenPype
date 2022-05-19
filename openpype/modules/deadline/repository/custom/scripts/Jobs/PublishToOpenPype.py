# -*- coding: utf-8 -*-
"""This is RR control plugin that runs on the job by user interaction.

It asks user for context to publish, getting it from OpenPype. In order to
run it needs `OPENPYPE_ROOT` to be set to know where to execute OpenPype.

"""
from Deadline.Scripting import MonitorUtils, ClientUtils  # noqa
from Deadline.Jobs import Job  # noqa
from System.IO import File, Path  # noqa
import subprocess
import os
import glob
import platform
import tempfile
import json
from typing import Union
import traceback


class OpenPypeContextSelector:
    """Class to handle publishing context determination in RR."""

    def __init__(self):
        self.jobs = MonitorUtils.GetSelectedJobs()
        self.context = {}

        self.openpype_executable = "openpype_gui"
        if platform.system().lower() == "windows":
            self.openpype_executable = "{}.exe".format(
                self.openpype_executable)

        op_path = os.environ.get("OPENPYPE_ROOT")
        print("initializing ... {}".format(op_path))
        if not op_path:
            print("Warning: OpenPype root is not found.")

            if platform.system().lower() == "windows":
                print("  * trying to find OpenPype on local computer.")
                op_path = os.path.join(
                    os.environ.get("PROGRAMFILES"),
                    "OpenPype", "openpype_console.exe"
                )
                if not os.path.exists(op_path):
                    # try to find in user local context
                    op_path = os.path.join(
                        os.environ.get("LOCALAPPDATA"),
                        "Programs",
                        "OpenPype", "openpype_console.exe"
                    )
                    if not os.path.exists(op_path):
                        raise Exception("Error: OpenPype was not found.")

                op_path = os.path.dirname(op_path)
                print("  - found OpenPype installation {}".format(op_path))

        self.openpype_root = op_path

    def _process_metadata_file(self):
        """Find and process metadata file.

        Try to find metadata json file in job folder to get context from.

        Returns:
            dict: Context from metadata json file.

        """
        image_dir = self.job.imageDir
        metadata_files = glob.glob(
            "{}{}*_metadata.json".format(image_dir, os.path.sep))
        if not metadata_files:
            return {}

        raise NotImplementedError(
            "Processing existing metadata not implemented yet.")

    @staticmethod
    def get_context_from_job(job: Job):
        return {"project": job.GetJobEnvironmentKeyValue('AVALON_PROJECT'),
                   "asset": job.GetJobEnvironmentKeyValue('AVALON_ASSET'),
                   "task": job.GetJobEnvironmentKeyValue('AVALON_TASK'),
                   "openpype": job.GetJobExtraInfoKeys().get("openpype_executables"),
                   "user": job.JobName}

    def process_jobs(self):
        """Process selected jobs.

        This should process selected jobs. If context can be determined
        automatically, no UI will be show and publishing will directly
        proceed.
        """
        show_context_selector = False
        for job in self.jobs:
            context = self.get_context_from_job(job)
            if any(key not in context for key in ("project", "asset", "task")):
                context = self.show()
                if not context:
                    raise ValueError("Cannot get job context for OpenPype")


        self.run_publish()

    def show(self) -> Union[dict, None]:
        """Show UI for context selection.

        Because of RR UI limitations, this must be done using OpenPype
        itself.

        Returns:
            dict: Context

        """
        tf = tempfile.TemporaryFile(delete=False)
        context_file = tf.name
        op_args = [os.path.join(self.openpype_root, self.openpype_executable),
                   "contextselection", tf.name]

        tf.close()
        print(">>> running {}".format(" ".join(op_args)))

        subprocess.call(op_args)

        with open(context_file, "r") as cf:
            context = json.load(cf)

        os.unlink(context_file)
        print(f">>> context: {context}")

        if not context or \
                not context.get("project") or \
                not context.get("asset") or \
                not context.get("task"):
            return {}
        return context

    @staticmethod
    def _show_rr_warning(text):
        warning_dialog = rrGlobal.getGenericUI()
        warning_dialog.addItem(rrGlobal.genUIType.label, "infoLabel", "")
        warning_dialog.setText("infoLabel", text)
        warning_dialog.addItem(
            rrGlobal.genUIType.layoutH, "btnLayout", "")
        warning_dialog.addItem(
            rrGlobal.genUIType.closeButton, "Ok", "btnLayout")
        warning_dialog.execute()
        del warning_dialog

    def create_publish_job(self, job: Job, context: dict):
        job_info_file = Path.Combine(ClientUtils.GetDeadlineTempPath(),
                                   "batch_job_info.job")
        writer = File.CreateText(jobInfoFile)


    def run_publish(self):
        """Run publish process."""
        env = {"AVALON_PROJECT": str(self.context.get("project")),
               "AVALON_ASSET": str(self.context.get("asset")),
               "AVALON_TASK": str(self.context.get("task")),
               # "AVALON_APP_NAME": str(self.context.get("app_name"))
               }

        print(">>> setting environment:")
        for k, v in env.items():
            print("    {}: {}".format(k, v))

        publishing_paths = [os.path.join(self.job.imageDir,
                                         os.path.dirname(
                                             self.job.imageFileName))]

        # add additional channels
        channel_idx = 0
        channel = self.job.channelFileName(channel_idx)
        while channel:
            channel_path = os.path.dirname(
                os.path.join(self.job.imageDir, channel))
            if channel_path not in publishing_paths:
                publishing_paths.append(channel_path)
            channel_idx += 1
            channel = self.job.channelFileName(channel_idx)

        args = [os.path.join(self.openpype_root, self.openpype_executable),
                'publish', '-t', "rr_control", "--gui"
                ]

        args += publishing_paths

        print(">>> running {}".format(" ".join(args)))
        orig = os.environ.copy()
        orig.update(env)
        try:
            subprocess.call(args, env=orig)
        except subprocess.CalledProcessError as e:
            self._show_rr_warning(" Publish failed [ {} ]".format(
                e.returncode
            ))


def __main__(*args):
    try:
        print("running selector")
        selector = OpenPypeContextSelector()

        # try to set context from environment
        selector.context["project"] = os.getenv("AVALON_PROJECT")
        selector.context["asset"] = os.getenv("AVALON_ASSET")
        selector.context["task"] = os.getenv("AVALON_TASK")
        # selector.context["app_name"] = os.getenv("AVALON_APP_NAME")

        # if anything inside is None, scratch the whole thing and
        # ask user for context.
        for _, v in selector.context.items():
            if not v:
                selector.context = {}
                break

        selector.process_jobs()
    except:
        ClientUtils.LogText("An unexpected error occurred:")
        ClientUtils.LogText(traceback.format_exc())
