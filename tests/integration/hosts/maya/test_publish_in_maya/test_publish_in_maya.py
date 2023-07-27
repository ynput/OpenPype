import os
import re
import shutil

import pytest

from tests.lib.assert_classes import DBAssert
from tests.integration.hosts.maya.lib import (
    MayaLocalPublishTestClass, LOG_PATH
)


class TestPublishInMaya(MayaLocalPublishTestClass):
    """Basic test case for publishing in Maya

        Shouldnt be running standalone only via 'runtests' pype command! (??)

        Uses generic TestCase to prepare fixtures for test data, testing DBs,
        env vars.

        Always pulls and uses test data from GDrive!

        Opens Maya, runs publish on prepared workile.

        Then checks content of DB (if subset, version, representations were
        created.
        Checks tmp folder if all expected files were published.

        How to run:
        (in cmd with activated {OPENPYPE_ROOT}/.venv)
        {OPENPYPE_ROOT}/.venv/Scripts/python.exe {OPENPYPE_ROOT}/start.py runtests ../tests/integration/hosts/maya  # noqa: E501

    """
    PERSIST = False

    APP_GROUP = "maya"

    # By default run through mayapy. For interactive mode, change to 2023 or
    # input `--app_variant 2023` in cli.
    APP_VARIANT = "py2023"

    TIMEOUT = 120  # publish timeout

    INPUT_DUMPS = os.path.join(
        os.path.dirname(__file__), "input", "dumps"
    )
    INPUT_ENVIRONMENT_JSON = os.path.join(
        os.path.dirname(__file__), "input", "env_vars", "env_var.json"
    )

    def running_in_mayapy(self, app_variant):
        app_variant = app_variant or self.APP_VARIANT

        # Running in mayapy.
        if app_variant.startswith("py"):
            return True

        # Running in maya.
        return False

    def get_usersetup_path(self):
        return os.path.join(
            os.path.dirname(__file__), "input", "startup", "userSetup.py"
        )

    @pytest.fixture(scope="module")
    def app_args(self, app_variant):
        args = []
        if self.running_in_mayapy(app_variant):
            args = ["-I", self.get_usersetup_path()]

        yield args

    @pytest.fixture(scope="module")
    def start_last_workfile(self, app_variant):
        """Returns url of workfile"""
        return not self.running_in_mayapy(app_variant)

    @pytest.fixture(scope="module")
    def last_workfile_path(self, download_test_data, output_folder):
        """Get last_workfile_path from source data.

            Maya expects workfile in proper folder, so copy is done first.
        """
        src_path = os.path.join(
            os.path.dirname(__file__),
            "input",
            "workfile",
            "test_project_test_asset_test_task_v001.ma"
        )
        dest_folder = os.path.join(
            output_folder,
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
    def startup_scripts(
        self, monkeypatch_session, download_test_data, app_variant
    ):
        """Points Maya to userSetup file from input data"""
        if not self.running_in_mayapy(app_variant):
            # Not needed for running MayaPy since the testing userSetup.py will
            # be passed in directly to the executable.
            original_pythonpath = os.environ.get("PYTHONPATH")
            monkeypatch_session.setenv(
                "PYTHONPATH",
                "{}{}{}".format(
                    os.path.dirname(self.get_usersetup_path()),
                    os.pathsep,
                    original_pythonpath
                )
            )

        monkeypatch_session.setenv(
            "MAYA_CMD_FILE_OUTPUT", os.path.join(download_test_data, LOG_PATH)
        )

    @pytest.fixture(scope="module")
    def skip_compare_folders(self):
        pass

    def test_publish(self, dbcon, publish_finished, download_test_data):
        logging_path = os.path.join(download_test_data, LOG_PATH)
        with open(logging_path, "r") as f:
            logging_output = f.read()

        # Check for pyblish errors.
        error_regex = r"pyblish \(ERROR\)((.|\n)*)"
        matches = re.findall(error_regex, logging_output)
        assert not matches, logging_output

        matches = re.findall(error_regex, publish_finished)
        assert not matches, publish_finished

        # Check for python errors.
        error_regex = r"// Error((.|\n)*)"
        matches = re.findall(error_regex, logging_output)
        assert not matches, logging_output

    def test_db_asserts(
        self,
        dbcon,
        publish_finished
    ):
        """Host and input data dependent expected results in DB."""
        print("test_db_asserts")
        failures = []
        failures.append(DBAssert.count_of_types(dbcon, "version", 2))

        failures.append(
            DBAssert.count_of_types(dbcon, "version", 0, name={"$ne": 1}))

        failures.append(
            DBAssert.count_of_types(dbcon, "subset", 1,
                                    name="modelMain"))

        failures.append(
            DBAssert.count_of_types(dbcon, "subset", 1,
                                    name="workfileTest_task"))

        failures.append(DBAssert.count_of_types(dbcon, "representation", 5))

        additional_args = {"context.subset": "modelMain",
                           "context.ext": "abc"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 2,
                                    additional_args=additional_args))

        additional_args = {"context.subset": "modelMain",
                           "context.ext": "ma"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 2,
                                    additional_args=additional_args))

        additional_args = {"context.subset": "workfileTest_task",
                           "context.ext": "ma"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 1,
                                    additional_args=additional_args))

        assert not any(failures)


if __name__ == "__main__":
    test_case = TestPublishInMaya()
