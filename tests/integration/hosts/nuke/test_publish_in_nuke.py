import logging

from tests.lib.assert_classes import DBAssert
from tests.integration.hosts.nuke.lib import NukeDeadlinePublishTestClass

log = logging.getLogger("test_publish_in_nuke")


class TestDeadlinePublishInNuke(NukeDeadlinePublishTestClass):
    """Basic test case for publishing in Nuke

        Uses generic TestCase to prepare fixtures for test data, testing DBs,
        env vars.

        !!!
        It expects modified path in WriteNode,
        use '[python {nuke.script_directory()}]' instead of regular root
        dir (eg. instead of `c:/projects`).
        Access file path by selecting WriteNode group, CTRL+Enter, update file
        input
        !!!

        Opens Nuke, run publish on prepared workile.

        Then checks content of DB (if subset, version, representations were
        created.
        Checks tmp folder if all expected files were published.

        How to run:
        (in cmd with activated {OPENPYPE_ROOT}/.venv)
        {OPENPYPE_ROOT}/.venv/Scripts/python.exe {OPENPYPE_ROOT}/start.py
        runtests ../tests/integration/hosts/nuke  # noqa: E501

        To check log/errors from launched app's publish process keep PERSIST
        to True and check `test_openpype.logs` collection.
    """
    # https://drive.google.com/file/d/1SUurHj2aiQ21ZIMJfGVBI2KjR8kIjBGI/view?usp=sharing  # noqa: E501
    TEST_FILES = [
        ("1SeWprClKhWMv2xVC9AcnekIJFExxnp_b",
         "test_nuke_deadline_publish.zip", "")
    ]

    APP_GROUP = "nuke"

    TIMEOUT = 180  # publish timeout

    # could be overwritten by command line arguments
    # keep empty to locate latest installed variant or explicit
    APP_VARIANT = ""
    PERSIST = False  # True - keep test_db, test_openpype, outputted test files
    TEST_DATA_FOLDER = None

    def test_db_asserts(self, dbcon, publish_finished):
        """Host and input data dependent expected results in DB."""
        print("test_db_asserts")
        failures = []

        failures.append(DBAssert.count_of_types(dbcon, "version", 2))

        failures.append(
            DBAssert.count_of_types(dbcon, "version", 0, name={"$ne": 1}))

        failures.append(
            DBAssert.count_of_types(dbcon, "subset", 1,
                                    name="renderTest_taskMain"))

        failures.append(
            DBAssert.count_of_types(dbcon, "subset", 1,
                                    name="workfileTest_task"))

        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 4))

        additional_args = {"context.subset": "workfileTest_task",
                           "context.ext": "nk"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 1,
                                    additional_args=additional_args))

        additional_args = {"context.subset": "renderTest_taskMain",
                           "context.ext": "exr"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 1,
                                    additional_args=additional_args))

        additional_args = {"context.subset": "renderTest_taskMain",
                           "name": "thumbnail"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 1,
                                    additional_args=additional_args))

        additional_args = {"context.subset": "renderTest_taskMain",
                           "name": "h264_mov"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 1,
                                    additional_args=additional_args))

        assert not any(failures)


if __name__ == "__main__":
    test_case = TestDeadlinePublishInNuke()
