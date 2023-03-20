import os
import pytest
import shutil

from tests.lib.testing_classes import (
    HostFixtures,
    PublishTest,
    DeadlinePublishTest

)


class AEHostFixtures(HostFixtures):
    @pytest.fixture(scope="module")
    def last_workfile_path(self, download_test_data, output_folder_url):
        """Get last_workfile_path from source data.

            Maya expects workfile in proper folder, so copy is done first.
        """
        src_path = os.path.join(download_test_data,
                                "input",
                                "workfile",
                                "test_project_test_asset_test_task_v001.aep")
        dest_folder = os.path.join(output_folder_url,
                                   self.PROJECT,
                                   self.ASSET,
                                   "work",
                                   self.TASK)
        os.makedirs(dest_folder)
        dest_path = os.path.join(dest_folder,
                                 "test_project_test_asset_test_task_v001.aep")
        shutil.copy(src_path, dest_path)

        yield dest_path

    @pytest.fixture(scope="module")
    def startup_scripts(self, monkeypatch_session, download_test_data):
        """Points Maya to userSetup file from input data"""
        pass

    @pytest.fixture(scope="module")
    def skip_compare_folders(self):
        # skip folder that contain "Logs", these come only from Deadline
        return ["Logs", "Auto-Save"]


class AELocalPublishTestClass(AEHostFixtures, PublishTest):
    """Testing class for local publishes."""


class AEDeadlinePublishTestClass(AEHostFixtures, DeadlinePublishTest):
    """Testing class for Deadline publishes."""
