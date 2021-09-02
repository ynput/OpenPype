import pytest
import sys
import os
import shutil

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
        """Copy"""
        startup_path = os.path.join(download_test_data,
                                    "input",
                                    "startup",
                                    "userSetup.py")
        from openpype.hosts import maya
        maya_dir = os.path.dirname(os.path.abspath(maya.__file__))
        shutil.move(os.path.join(maya_dir, "startup", "userSetup.py"),
                    os.path.join(maya_dir, "startup", "userSetup.tmp")
                    )
        shutil.copy(startup_path,
                    os.path.join(maya_dir, "startup", "userSetup.py"))
        yield os.path.join(maya_dir, "startup", "userSetup.py")

        shutil.move(os.path.join(maya_dir, "startup", "userSetup.tmp"),
                    os.path.join(maya_dir, "startup", "userSetup.py"))

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
        while launched_app.poll() is None:
            time.sleep(0.5)

        # some clean exit test possible?
        print("Publish finished")

    def test_db_asserts(self, dbcon, publish_finished):
        print("test_db_asserts")
        assert 5 == dbcon.find({"type": "version"}).count(), \
            "Not expected no of versions"

        assert 0 == \
               dbcon.find({"type": "version", "name": {"$ne": 1}}).count(), \
                   "Only versions with 1 expected"

        assert 1 == \
               dbcon.find({"type": "subset", "name": "modelMain"}).count(), \
                   "modelMain subset must be present"

        assert 1 == \
               dbcon.find(
                   {"type": "subset", "name": "workfileTest_task"}).count(), \
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

    def test_files(self, dbcon, publish_finished, download_test_data):
        print("test_files")
        # hero files
        hero_folder = os.path.join(download_test_data,
                                   self.PROJECT,
                                   self.ASSET,
                                   "publish",
                                   "model",
                                   "modelMain",
                                   "hero")

        assert os.path.exists(
            os.path.join(hero_folder,
                         "test_project_test_asset_modelMain_hero.ma")
        ), "test_project_test_asset_modelMain_hero.ma doesn't exist"

        assert os.path.exists(
            os.path.join(hero_folder,
                         "test_project_test_asset_modelMain_hero.abc")
        ), "test_project_test_asset_modelMain_hero.abc doesn't exist"

        # version files
        version_folder = os.path.join(download_test_data,
                                      self.PROJECT,
                                      self.ASSET,
                                      "publish",
                                      "model",
                                      "modelMain",
                                      "v001")

        assert os.path.exists(
            os.path.join(version_folder,
                         "test_project_test_asset_modelMain_v001.ma")
        ), "test_project_test_asset_modelMain_v001.ma doesn't exist"

        assert os.path.exists(
            os.path.join(version_folder,
                         "test_project_test_asset_modelMain_v001.abc")
        ), "test_project_test_asset_modelMain_v001.abc doesn't exist"

        # workfile files
        workfile_folder = os.path.join(download_test_data,
                                       self.PROJECT,
                                       self.ASSET,
                                       "publish",
                                       "workfile",
                                       "workfileTest_task",
                                       "v001")

        assert os.path.exists(
            os.path.join(workfile_folder,
                         "test_project_test_asset_workfileTest_task_v001.mb")
        ), "test_project_test_asset_workfileTest_task_v001.mb doesn't exist"

if __name__ == "__main__":
    test_case = TestPublishInMaya()
