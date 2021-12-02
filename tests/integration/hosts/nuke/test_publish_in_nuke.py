import pytest
import os
import shutil
import logging

from tests.lib.testing_classes import PublishTest

log = logging.getLogger("test_publish_in_nuke")


class TestPublishInNuke(PublishTest):
    """Basic test case for publishing in Nuke

        Uses generic TestCase to prepare fixtures for test data, testing DBs,
        env vars.

        Opens Nuke, run publish on prepared workile.

        Then checks content of DB (if subset, version, representations were
        created.
        Checks tmp folder if all expected files were published.

        How to run:
        {OPENPYPE_ROOT}/.venv/Scripts/python.exe {OPENPYPE_ROOT}/start.py runtests ../tests/integration/hosts/nuke  # noqa: E501

    """
    PERSIST = True  # True - keep test_db, test_openpype, outputted test files

    TEST_FILES = [
        ("1SUurHj2aiQ21ZIMJfGVBI2KjR8kIjBGI", "test_Nuke_publish.zip", "")
    ]

    APP = "nuke"
    APP_VARIANT = "12-2"

    APP_NAME = "{}/{}".format(APP, APP_VARIANT)

    TIMEOUT = 120  # publish timeout

    @pytest.fixture(scope="module")
    def last_workfile_path(self, download_test_data):
        """Get last_workfile_path from source data.

            Maya expects workfile in proper folder, so copy is done first.
        """
        log.info("log last_workfile_path")
        src_path = os.path.join(
            download_test_data,
            "input",
            "workfile",
            "test_project_test_asset_CompositingInNuke_v001.nk")
        dest_folder = os.path.join(download_test_data,
                                   self.PROJECT,
                                   self.ASSET,
                                   "work",
                                   self.TASK)
        os.makedirs(dest_folder)
        dest_path = os.path.join(
            dest_folder, "test_project_test_asset_CompositingInNuke_v001.nk")
        shutil.copy(src_path, dest_path)

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

    def test_db_asserts(self, dbcon, publish_finished):
        """Host and input data dependent expected results in DB."""
        print("test_db_asserts")
        assert 5 == dbcon.count_documents({"type": "version"}), \
            "Not expected no of versions"

        assert 0 == dbcon.count_documents({"type": "version",
                                           "name": {"$ne": 1}}), \
            "Only versions with 1 expected"

        assert 1 == dbcon.count_documents({"type": "subset",
                                           "name": "renderCompositingInNukeMain"}  # noqa: E501
                                          ), \
            "renderCompositingInNukeMain subset must be present"

        assert 1 == dbcon.count_documents({"type": "subset",
                                           "name": "workfileTest_task"}), \
            "workfileTest_task subset must be present"

        assert 10 == dbcon.count_documents({"type": "representation"}), \
            "Not expected no of representations"

        assert 1 == dbcon.count_documents({"type": "representation",
                                           "context.subset": "renderCompositingInNukeMain",  # noqa: E501
                                           "context.ext": "exr"}), \
            "Not expected no of representations with ext 'exr'"


if __name__ == "__main__":
    test_case = TestPublishInNuke()
