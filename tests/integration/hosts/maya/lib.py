import os
import pytest
import shutil

from tests.lib.testing_classes import (
    HostFixtures,
    PublishTest,
    DeadlinePublishTest
)


LOG_PATH = os.path.join("output.log")


class MayaHostFixtures(HostFixtures):
    @pytest.fixture(scope="module")
    def last_workfile_path(self, download_test_data, output_folder_url):
        """Get last_workfile_path from source data.

            Maya expects workfile in proper folder, so copy is done first.
        """
        src_path = os.path.join(
            os.path.dirname(__file__), "resources", "workfile.ma"
        )
        dest_folder = os.path.join(
            output_folder_url,
            self.PROJECT_NAME,
            self.ASSET_NAME,
            "work",
            self.TASK_NAME
        )
        os.makedirs(dest_folder)
        dest_path = os.path.join(
            dest_folder, "test_project_test_asset_test_task_v001.ma"
        )
        shutil.copy(src_path, dest_path)

        yield dest_path

    @pytest.fixture(scope="module")
    def startup_scripts(self, monkeypatch_session, download_test_data):
        """Points Maya to userSetup file from input data"""
        user_setup_path = os.path.join(os.path.dirname(__file__), "resources")
        original_pythonpath = os.environ.get("PYTHONPATH")
        monkeypatch_session.setenv(
            "PYTHONPATH",
            "{}{}{}".format(
                user_setup_path, os.pathsep, original_pythonpath
            )
        )

        monkeypatch_session.setenv(
            "MAYA_CMD_FILE_OUTPUT", os.path.join(download_test_data, LOG_PATH)
        )

    @pytest.fixture(scope="module")
    def skip_compare_folders(self):
        yield []


class MayaLocalPublishTestClass(MayaHostFixtures, PublishTest):
    """Testing class for local publishes."""


class MayaDeadlinePublishTestClass(MayaHostFixtures, DeadlinePublishTest):
    """Testing class for Deadline publishes."""
