import os
import shutil
import re

import pytest

from tests.lib.assert_classes import DBAssert
from tests.lib.testing_classes import HostFixtures, PublishTest


class MayaFixtures(HostFixtures):

    # By default run through mayapy. For interactive mode, change to "maya" or
    # input `--app_group maya` in cli.
    APP_GROUP = "mayapy"

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

    def get_log_path(self, dirpath, app_variant):
        return os.path.join(
            dirpath, "output_{}.log".format(app_variant)
        )

    @pytest.fixture(scope="module")
    def app_args(self, app_group, app_variant):
        args = []

        if self.running_in_mayapy(app_group):
            # Attempts to run MayaPy in 2022 has failed.
            msg = "Maya 2022 and older is not supported through MayaPy"
            assert int(app_variant) > 2022, msg

            # Maya 2023+ can isolate from the users environment. Although the
            # command flag is present in older versions of Maya, it does not
            # work resulting a fatal python error:
            # Fatal Python error: initfsencoding: unable to load the file
            #    system codec
            # ModuleNotFoundError: No module named 'encodings'
            args.append("-I")

            # MayaPy can only be passed a python script, so Maya scene opening
            # will happen post launch.
            args.append(self.get_usersetup_path())

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
        data_folder, output_folder, _ = setup_fixture

        source_folder = (
            self.INPUT_WORKFILE or
            os.path.join(data_folder, "input", "workfile")
        )
        filename = os.listdir(source_folder)[0]
        src_path = os.path.join(source_folder, filename)
        dest_folder = os.path.join(
            output_folder,
            self.PROJECT_NAME,
            self.ASSET_NAME,
            "work",
            self.TASK_NAME
        )
        os.makedirs(dest_folder)
        dest_path = os.path.join(dest_folder, filename)
        shutil.copy(src_path, dest_path)

        yield dest_path

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


class TestPublishInMaya(MayaFixtures, PublishTest):
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

    EXPECTED_FOLDER = os.path.join(os.path.dirname(__file__), "expected")
    INPUT_DUMPS = os.path.join(os.path.dirname(__file__), "input", "dumps")
    INPUT_ENVIRONMENT_JSON = os.path.join(
        os.path.dirname(__file__), "input", "env_vars", "env_var.json"
    )
    INPUT_WORKFILE = os.path.join(
        os.path.dirname(__file__), "input", "workfile"
    )

    FILES = []

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

        print(("-" * 50) + "LOGGING" + ("-" * 50))
        print(logging_output)
        print(("-" * 50) + "PUBLISH" + ("-" * 50))
        print(publish_finished)

        # Check for pyblish errors.
        error_regex = r"pyblish \(ERROR\)((.|\n)*?)((pyblish \())"
        matches = re.findall(error_regex, logging_output)
        assert not matches, matches[0][0]

        matches = re.findall(error_regex, publish_finished)
        assert not matches, matches[0][0]

        # Check for python errors.
        error_regex = r"// Error((.|\n)*)"
        matches = re.findall(error_regex, logging_output)
        assert not matches, matches[0][0]

    def test_db_asserts(self, dbcon, deadline_finished):
        """Host and input data dependent expected results in DB."""
        print("test_db_asserts")
        asserts = []
        asserts.append(DBAssert.count_of_types(dbcon, "version", 3))

        asserts.append(
            DBAssert.count_of_types(dbcon, "version", 0, name={"$ne": 1})
        )

        asserts.append(
            DBAssert.count_of_types(dbcon, "subset", 1, name="modelMain")
        )

        asserts.append(
            DBAssert.count_of_types(
                dbcon, "subset", 1, name="workfileTest_task"
            )
        )

        asserts.append(DBAssert.count_of_types(dbcon, "representation", 8))

        asserts.append(
            DBAssert.count_of_types(
                dbcon,
                "representation",
                2,
                additional_args={
                    "context.subset": "modelMain", "context.ext": "abc"
                }
            )
        )

        asserts.append(
            DBAssert.count_of_types(
                dbcon,
                "representation",
                2,
                additional_args={
                    "context.subset": "modelMain", "context.ext": "ma"
                }
            )
        )

        asserts.append(
            DBAssert.count_of_types(
                dbcon,
                "representation",
                1,
                additional_args={
                    "context.subset": "workfileTest_task", "context.ext": "ma"
                }
            )
        )

        asserts.append(
            DBAssert.count_of_types(
                dbcon, "subset", 1, name="renderMain_beauty"
            )
        )

        asserts.append(
            DBAssert.count_of_types(
                dbcon,
                "representation",
                1,
                additional_args={
                    "context.subset": "renderMain_beauty",
                    "context.ext": "exr"
                }
            )
        )

        asserts.append(
            DBAssert.count_of_types(
                dbcon,
                "representation",
                1,
                additional_args={
                    "context.subset": "renderMain_beauty",
                    "context.ext": "jpg"
                }
            )
        )

        asserts.append(
            DBAssert.count_of_types(
                dbcon,
                "representation",
                1,
                additional_args={
                    "context.subset": "renderMain_beauty",
                    "context.ext": "png"
                }
            )
        )

        failures = [x for x in asserts if x is not None]
        msg = "Failures:\n" + "\n".join(failures)
        assert not failures, msg


if __name__ == "__main__":
    test_case = TestPublishInMaya()
