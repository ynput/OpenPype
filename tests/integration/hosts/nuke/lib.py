import os
import pytest
import re

from tests.lib.testing_classes import (
    HostFixtures,
    PublishTest,
    DeadlinePublishTest
)


class NukeHostFixtures(HostFixtures):
    @pytest.fixture(scope="module")
    def last_workfile_path(self, download_test_data, output_folder_url):
        """Get last_workfile_path from source data.

        """
        source_file_name = "test_project_test_asset_test_task_v001.nk"
        src_path = os.path.join(download_test_data,
                                "input",
                                "workfile",
                                source_file_name)
        dest_folder = os.path.join(output_folder_url,
                                   self.PROJECT,
                                   self.ASSET,
                                   "work",
                                   self.TASK)
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)

        dest_path = os.path.join(dest_folder,
                                 source_file_name)

        # rewrite old root with temporary file
        # TODO - using only C:/projects seems wrong - but where to get root ?
        replace_pattern = re.compile(re.escape("C:/projects"), re.IGNORECASE)
        with open(src_path, "r") as fp:
            updated = fp.read()
            updated = replace_pattern.sub(output_folder_url.replace("\\", '/'),
                                          updated)

        with open(dest_path, "w") as fp:
            fp.write(updated)

        yield dest_path

    @pytest.fixture(scope="module")
    def startup_scripts(self, monkeypatch_session, download_test_data):
        """Points Nuke to userSetup file from input data"""
        startup_path = os.path.join(download_test_data,
                                    "input",
                                    "startup")
        original_nuke_path = os.environ.get("NUKE_PATH", "")
        monkeypatch_session.setenv("NUKE_PATH",
                                   "{}{}{}".format(startup_path,
                                                   os.pathsep,
                                                   original_nuke_path))

    @pytest.fixture(scope="module")
    def skip_compare_folders(self):
        yield []

class NukeLocalPublishTestClass(NukeHostFixtures, PublishTest):
    """Testing class for local publishes."""


class NukeDeadlinePublishTestClass(NukeHostFixtures, DeadlinePublishTest):
    """Testing class for Deadline publishes."""
