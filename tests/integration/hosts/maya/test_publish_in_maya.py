import re
import os

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

    TEST_FILES = [
        ("test_publish_in_maya", "", "")
    ]

    APP_GROUP = "maya"
    # keep empty to locate latest installed variant or explicit
    APP_VARIANT = ""

    TIMEOUT = 120  # publish timeout

    def test_publish(
        self,
        dbcon,
        publish_finished,
        download_test_data
    ):
        """Testing Pyblish and Python logs within Maya."""

        # All maya output via MAYA_CMD_FILE_OUTPUT env var during test run
        logging_path = os.path.join(download_test_data, "output.log")
        with open(logging_path, "r") as f:
            logging_output = f.read()

        print(("-" * 50) + "LOGGING" + ("-" * 50))
        print(logging_output)

        # Check for pyblish errors.
        error_regex = r"pyblish \(ERROR\)((.|\n)*?)((pyblish \())"
        matches = re.findall(error_regex, logging_output)
        assert not matches, matches[0][0]

        # Check for python errors.
        error_regex = r"// Error((.|\n)*)"
        matches = re.findall(error_regex, logging_output)
        assert not matches, matches[0][0]

    def test_db_asserts(self, dbcon, publish_finished):
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
