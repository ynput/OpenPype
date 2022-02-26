# -*- coding: utf-8 -*-
"""This is RR control plugin that runs on the job by user interaction.

It asks user for context to publish, getting it from OpenPype. In order to
run it needs `OPENPYPE_ROOT` to be set to know where to execute OpenPype.

"""
import rr  # noqa
import rrGlobal  # noqa
import subprocess
import os
import glob
import platform
import tempfile
import json


class OpenPypeContextSelector:
    """Class to handle publishing context determination in RR."""

    def __init__(self):
        self.job = rr.getJob()
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

    def process_job(self):
        """Process selected job.

        This should process selected job. If context can be determined
        automatically, no UI will be show and publishing will directly
        proceed.
        """
        if not self.context and not self.show():
            return

        self.context["user"] = self.job.userName
        self.run_publish()

    def show(self):
        """Show UI for context selection.

        Because of RR UI limitations, this must be done using OpenPype
        itself.

        """
        tf = tempfile.TemporaryFile(delete=False)
        context_file = tf.name
        op_args = [os.path.join(self.openpype_root, self.openpype_executable),
                   "contextselection", tf.name]

        tf.close()
        print(">>> running {}".format(" ".join(op_args)))

        subprocess.call(op_args)

        with open(context_file, "r") as cf:
            self.context = json.load(cf)

        os.unlink(context_file)
        print(">>> context: {}".format(self.context))

        if not self.context or \
                not self.context.get("project") or \
                not self.context.get("asset") or \
                not self.context.get("task"):
            self._show_rr_warning("Context selection failed.")
            return False

        # self.context["app_name"] = self.job.renderer.name
        # there should be mapping between OpenPype and Royal Render
        # app names and versions, but since app_name is not used
        # currently down the line (but it is required by OP publish command
        # right now).
        self.context["app_name"] = "maya/2020"
        return True

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

    def run_publish(self):
        """Run publish process."""
        env = {"AVALON_PROJECT": str(self.context.get("project")),
               "AVALON_ASSET": str(self.context.get("asset")),
               "AVALON_TASK": str(self.context.get("task")),
               "AVALON_APP_NAME": str(self.context.get("app_name"))}

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


print("running selector")
selector = OpenPypeContextSelector()

# try to set context from environment
selector.context["project"] = os.getenv("AVALON_PROJECT")
selector.context["asset"] = os.getenv("AVALON_ASSET")
selector.context["task"] = os.getenv("AVALON_TASK")
selector.context["app_name"] = os.getenv("AVALON_APP_NAME")

# if anything inside is None, scratch the whole thing and
# ask user for context.
for _, v in selector.context.items():
    if not v:
        selector.context = {}
        break

selector.process_job()
