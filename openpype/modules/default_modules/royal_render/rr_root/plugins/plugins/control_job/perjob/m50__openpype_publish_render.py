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
        self.context = None

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
                if os.path.exists(op_path):
                    print("  - found OpenPype installation {}".format(op_path))
                else:
                    # try to find in user local context
                    op_path = os.path.join(
                        os.environ.get("LOCALAPPDATA"),
                        "Programs"
                        "OpenPype", "openpype_console.exe"
                    )
                    if os.path.exists(op_path):
                        print(
                            "  - found OpenPype installation {}".format(
                                op_path))
                    else:
                        raise Exception("Error: OpenPype was not found.")

        self.openpype_root = op_path

        # TODO: this should try to find metadata file. Either using
        #       jobs custom attributes or using environment variable
        #       or just using plain existence of file.
        # self.context = self._process_metadata_file()

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
        if not self.context:
            self.show()

    def show(self):
        """Show UI for context selection.

        Because of RR UI limitations, this must be done using OpenPype
        itself.

        """
        op_exec = "openpype_gui"
        if platform.system().lower() == "windows":
            op_exec = "{}.exe".format(op_exec)

        with tempfile.TemporaryFile() as tf:
            op_args = [os.path.join(self.openpype_root, op_exec),
                    "contextselection", tf.name]

            print(">>> running {}".format(op_args))
            subprocess.call(op_args)
            self.context = json.load(tf)

        if not self.context or \
                not self.context.project or \
                not self.context.asset or \
                not self.context.task:
            self._show_rr_warning("Context selection failed.")
            return

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


print("running selector")
selector = OpenPypeContextSelector()
selector.process_job()
