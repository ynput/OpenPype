import os
import re
import shutil

import pytest

from tests.lib.assert_classes import DBAssert
from tests.integration.hosts.maya.lib import MayaLocalPublishTestClass


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

    # By default run through mayapy. For interactive mode, change to "maya" or
    # input `--app_group maya` in cli.
    APP_GROUP = "mayapy"

    # By default running latest version of Maya.
    APP_VARIANT = ""

    TIMEOUT = 120  # publish timeout

    INPUT_DUMPS = os.path.join(
        os.path.dirname(__file__), "input", "dumps"
    )
    INPUT_ENVIRONMENT_JSON = os.path.join(
        os.path.dirname(__file__), "input", "env_vars", "env_var.json"
    )

    FILES = [
        ("1BTSIIULJTuDc8VvXseuiJV_fL6-Bu7FP", "test_maya_publish.zip", "")
    ]

    def running_in_mayapy(self, app_group):
        app_group = app_group or self.APP_GROUP

        # Running in mayapy.
        if app_group == "mayapy":
            return True

        # Running in maya.
        return False

    def get_usersetup_path(self):
        return os.path.join(
            os.path.dirname(__file__), "input", "startup", "userSetup.py"
        )

    @pytest.fixture(scope="module")
    def app_args(self, app_group, app_variant):
        # We should try and support 2020?
        msg = "Maya 2020 and below is not supported for testing."
        assert int(app_variant) > 2020, msg

        args = []
        if self.running_in_mayapy(app_group):
            args = ["-I", self.get_usersetup_path()]

        yield args

    @pytest.fixture(scope="module")
    def start_last_workfile(self, app_group):
        """Returns url of workfile"""
        return not self.running_in_mayapy(app_group)

    @pytest.fixture(scope="module")
    def last_workfile_path(self, setup_fixture):
        """Get last_workfile_path from source data.

            Maya expects workfile in proper folder, so copy is done first.
        """
        _, output_folder, _ = setup_fixture

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

    def get_log_path(self, dirpath, app_variant):
        return os.path.join(
            dirpath, "output_{}.log".format(app_variant)
        )

    @pytest.fixture(scope="module")
    def startup_scripts(
        self, monkeypatch_session, setup_fixture, app_group, app_variant
    ):
        data_folder, _, _ = setup_fixture

        """Points Maya to userSetup file from input data"""
        if not self.running_in_mayapy(app_group):
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
            "MAYA_CMD_FILE_OUTPUT",
            self.get_log_path(data_folder, app_variant)
        )

    @pytest.fixture(scope="module")
    def skip_compare_folders(self):
        pass

    def test_publish(
        self,
        dbcon,
        publish_finished,
        setup_fixture,
        app_variant
    ):
        data_folder, _, _ = setup_fixture

        logging_path = self.get_log_path(data_folder, app_variant)
        with open(logging_path, "r") as f:
            logging_output = f.read()

        print(logging_output)
        print(publish_finished)

        # Check for pyblish errors.
        error_regex = r"pyblish \(ERROR\)((.|\n)*)"
        matches = re.findall(error_regex, logging_output)
        assert not matches, matches[0][0]

        matches = re.findall(error_regex, publish_finished)
        assert not matches, matches[0][0]

        # Check for python errors.
        error_regex = r"// Error((.|\n)*)"
        matches = re.findall(error_regex, logging_output)
        assert not matches, matches[0][0]

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
