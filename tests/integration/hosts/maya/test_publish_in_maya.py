import pytest
import sys
import os
import shutil
import glob

from tests.lib.testing_classes import PublishTest


class TestPublishInMaya(PublishTest):
    """Basic test case for publishing in Maya

        Uses generic TestCase to prepare fixtures for test data, testing DBs,
        env vars.

        Opens Maya, run publish on prepared workile.

        Then checks content of DB (if subset, version, representations were
        created.
        Checks tmp folder if all expected files were published.

    """
    PERSIST = True

    TEST_FILES = [
        ("1pOwjA_VVBc6ooTZyFxtAwLS2KZHaBlkY", "test_maya_publish.zip", "")
    ]

    APP = "maya"
    APP_VARIANT = "2019"

    APP_NAME = "{}/{}".format(APP, APP_VARIANT)

    TIMEOUT = 120  # publish timeout

    @pytest.fixture(scope="module")
    def last_workfile_path(self, download_test_data):
        """Get last_workfile_path from source data.

            Maya expects workfile in proper folder, so copy is done first.
        """
        src_path = os.path.join(download_test_data,
                                "input",
                                "workfile",
                                "test_project_test_asset_TestTask_v001.mb")
        dest_folder = os.path.join(download_test_data,
                                   self.PROJECT,
                                   self.ASSET,
                                   "work",
                                   self.TASK)
        os.makedirs(dest_folder)
        dest_path = os.path.join(dest_folder,
                                 "test_project_test_asset_TestTask_v001.mb")
        shutil.copy(src_path, dest_path)

        yield dest_path

    @pytest.fixture(scope="module")
    def startup_scripts(self, monkeypatch_session, download_test_data):
        """Points Maya to userSetup file from input data"""
        startup_path = os.path.join(download_test_data,
                                    "input",
                                    "startup")
        original_pythonpath = os.environ.get("PYTHONPATH")
        monkeypatch_session.setenv("PYTHONPATH",
                                   "{};{}".format(original_pythonpath,
                                                  startup_path))

    def test_db_asserts(self, dbcon, publish_finished):
        """Host and input data dependent expected results in DB."""
        print("test_db_asserts")
        assert 5 == dbcon.find({"type": "version"}).count(), \
            "Not expected no of versions"

        assert 0 == dbcon.find({"type": "version",
                                "name": {"$ne": 1}}).count(), \
            "Only versions with 1 expected"

        assert 1 == dbcon.find({"type": "subset",
                                "name": "modelMain"}).count(), \
            "modelMain subset must be present"

        assert 1 == dbcon.find({"type": "subset",
                                "name": "workfileTest_task"}).count(), \
            "workfileTest_task subset must be present"

        assert 11 == dbcon.find({"type": "representation"}).count(), \
            "Not expected no of representations"

        assert 2 == dbcon.find({"type": "representation",
                                "context.subset": "modelMain",
                                "context.ext": "abc"}).count(), \
            "Not expected no of representations with ext 'abc'"

        assert 2 == dbcon.find({"type": "representation",
                                "context.subset": "modelMain",
                                "context.ext": "ma"}).count(), \
            "Not expected no of representations with ext 'abc'"


if __name__ == "__main__":
    test_case = TestPublishInMaya()
