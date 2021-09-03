import pytest
import sys
import os
import shutil
import glob

from tests.lib.testing_wrapper import TestCase


class TestPublishInMaya(TestCase):
    """Basic test case for publishing in Maya

        Uses generic TestCase to prepare fixtures for test data, testing DBs,
        env vars.

        Opens Maya, run publish on prepared workile.

        Then checks content of DB (if subset, version, representations were
        created.
        Checks tmp folder if all expected files were published.

    """
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
                                "data",
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

    @pytest.fixture(scope="module")
    def launched_app(self, dbcon, download_test_data, last_workfile_path,
                     startup_scripts):
        """Get sync_server_module from ModulesManager"""
        root_key = "config.roots.work.{}".format("windows")  # TEMP
        dbcon.update_one(
            {"type": "project"},
            {"$set":
                {
                    root_key: download_test_data
                }}
        )

        from openpype import PACKAGE_DIR

        # Path to OpenPype's schema
        schema_path = os.path.join(
            os.path.dirname(PACKAGE_DIR),
            "schema"
        )
        os.environ["AVALON_SCHEMA"] = schema_path  # TEMP

        import openpype
        openpype.install()
        os.environ["OPENPYPE_EXECUTABLE"] = sys.executable
        from openpype.lib import ApplicationManager

        application_manager = ApplicationManager()
        data = {
            "last_workfile_path": last_workfile_path,
            "start_last_workfile": True,
            "project_name": self.PROJECT,
            "asset_name": self.ASSET,
            "task_name": self.TASK
        }

        yield application_manager.launch(self.APP_NAME, **data)

    @pytest.fixture(scope="module")
    def publish_finished(self, dbcon, launched_app):
        """Dummy fixture waiting for publish to finish"""
        import time
        time_start = time.time()
        while launched_app.poll() is None:
            time.sleep(0.5)
            if time.time() - time_start > self.TIMEOUT:
                raise ValueError("Timeout reached")

        # some clean exit test possible?
        print("Publish finished")
        yield True

    def test_db_asserts(self, dbcon, publish_finished):
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

    def test_folder_structure_same(self, dbcon, publish_finished,
                                   download_test_data):
        """Check if expected and published subfolders contain same files.

            Compares only presence, not size nor content!
        """
        published_dir_base = download_test_data
        published_dir = os.path.join(published_dir_base,
                                     self.PROJECT,
                                     self.TASK,
                                     "**")
        expected_dir_base = os.path.join(published_dir_base,
                                         "expected")
        expected_dir = os.path.join(expected_dir_base,
                                    self.PROJECT,
                                    self.TASK,
                                    "**")

        published = set(f.replace(published_dir_base, '') for f in
                        glob.glob(published_dir, recursive=True) if
                        f != published_dir_base and os.path.exists(f))
        expected = set(f.replace(expected_dir_base, '') for f in
                       glob.glob(expected_dir, recursive=True) if
                       f != expected_dir_base and os.path.exists(f))

        not_matched = expected.difference(published)
        assert not not_matched, "Missing {} files".format(not_matched)


if __name__ == "__main__":
    test_case = TestPublishInMaya()
