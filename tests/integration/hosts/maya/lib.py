import os
import pytest
import shutil

from tests.lib.testing_classes import (
    HostFixtures,
    PublishTest,
    DeadlinePublishTest
)


class MayaHostFixtures(HostFixtures):

    def running_in_mayapy(self, app_group):
        app_group = app_group or self.APP_GROUP

        # Running in mayapy.
        if app_group == "mayapy":
            return True

        # Running in maya.
        return False

    @pytest.fixture(scope="module")
    def start_last_workfile(self, app_group):
        """Returns url of workfile"""
        return not self.running_in_mayapy(app_group)

    @pytest.fixture(scope="module")
    def last_workfile_path(self, download_test_data, output_folder_url):
        """Get last_workfile_path from source data.

            Maya expects workfile in proper folder, so copy is done first.
        """
        src_path = os.path.join(
            download_test_data,
            "input",
            "workfile",
            "test_project_test_asset_test_task_v001.ma"
        )
        dest_folder = os.path.join(
            output_folder_url,
            self.PROJECT,
            self.ASSET,
            "work",
            self.TASK
        )

        os.makedirs(dest_folder)

        dest_path = os.path.join(
            dest_folder, "test_project_test_asset_test_task_v001.ma"
        )
        shutil.copy(src_path, dest_path)

        yield dest_path

    @pytest.fixture(scope="module")
    def startup_scripts(
        self, monkeypatch_session, download_test_data, app_group
    ):
        """Points Maya to userSetup file from input data"""
        monkeypatch_session.setenv(
            "MAYA_CMD_FILE_OUTPUT",
            os.path.join(download_test_data, "output.log")
        )

        if not self.running_in_mayapy(app_group):
            # Not needed for running MayaPy since the testing userSetup.py will
            # be passed in directly to the executable.
            startup_path = os.path.join(
                download_test_data, "input", "startup"
            )
            original_pythonpath = os.environ.get("PYTHONPATH")
            monkeypatch_session.setenv(
                "PYTHONPATH",
                "{}{}{}".format(startup_path, os.pathsep, original_pythonpath)
            )

    @pytest.fixture(scope="module")
    def skip_compare_folders(self):
        yield []

    @pytest.fixture(scope="module")
    def app_args(self, download_test_data, app_group, keep_app_open):
        args = []

        if keep_app_open and self.running_in_mayapy(app_group):
            # Inspect interactively after running script; forces a prompt even
            # if stdin does not appear to be a terminal.
            args.append("-i")

        if self.running_in_mayapy(app_group):
            # MayaPy can only be passed a python script, so Maya scene opening
            # will happen post launch.
            args.append(
                os.path.join(
                    download_test_data, "input", "startup", "userSetup.py"
                )
            )

        yield args


class MayaLocalPublishTestClass(MayaHostFixtures, PublishTest):
    """Testing class for local publishes."""


class MayaDeadlinePublishTestClass(MayaHostFixtures, DeadlinePublishTest):
    """Testing class for Deadline publishes."""
