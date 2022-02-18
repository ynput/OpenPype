import pytest
import os
import shutil

from tests.lib.testing_classes import PublishTest


class TestPublishInAfterEffects(PublishTest):
    """Basic test case for publishing in AfterEffects

        Uses generic TestCase to prepare fixtures for test data, testing DBs,
        env vars.

        Opens AfterEffects, run publish on prepared workile.

        Test zip file sets 3 required env vars:
        - HEADLESS_PUBLISH - this triggers publish immediately app is open
        - IS_TEST - this differentiate between regular webpublish
        - PYBLISH_TARGETS

        Then checks content of DB (if subset, version, representations were
        created.
        Checks tmp folder if all expected files were published.

    """
    PERSIST = True

    TEST_FILES = [
        ("1c8261CmHwyMgS-g7S4xL5epAp0jCBmhf",
         "test_aftereffects_publish.zip",
         "")
    ]

    APP = "aftereffects"
    APP_VARIANT = "2022"

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
                                "test_project_test_asset_TestTask_v001.aep")
        dest_folder = os.path.join(download_test_data,
                                   self.PROJECT,
                                   self.ASSET,
                                   "work",
                                   self.TASK)
        os.makedirs(dest_folder)
        dest_path = os.path.join(dest_folder,
                                 "test_project_test_asset_TestTask_v001.aep")
        shutil.copy(src_path, dest_path)

        yield dest_path

    @pytest.fixture(scope="module")
    def startup_scripts(self, monkeypatch_session, download_test_data):
        """Points AfterEffects to userSetup file from input data"""
        pass

    def test_db_asserts(self, dbcon, publish_finished):
        """Host and input data dependent expected results in DB."""
        print("test_db_asserts")

        assert 2 == dbcon.count_documents({"type": "version"}), \
            "Not expected no of versions"

        assert 0 == dbcon.count_documents({"type": "version",
                                           "name": {"$ne": 1}}), \
            "Only versions with 1 expected"

        assert 1 == dbcon.count_documents({"type": "subset",
                                           "name": "imageMainBackgroundcopy"
                                           }), \
            "modelMain subset must be present"

        assert 1 == dbcon.count_documents({"type": "subset",
                                           "name": "workfileTest_task"}), \
            "workfileTesttask subset must be present"

        assert 1 == dbcon.count_documents({"type": "subset",
                                           "name": "reviewTesttask"}), \
            "reviewTesttask subset must be present"

        assert 4 == dbcon.count_documents({"type": "representation"}), \
            "Not expected no of representations"

        assert 1 == dbcon.count_documents({"type": "representation",
                                           "context.subset": "renderTestTaskDefault",  # noqa E501
                                           "context.ext": "png"}), \
            "Not expected no of representations with ext 'png'"


if __name__ == "__main__":
    test_case = TestPublishInAfterEffects()
