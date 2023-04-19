import logging

from tests.integration.hosts.nuke.lib import NukeLocalSyntheticTestClass

log = logging.getLogger("test_workfile_create")


class TestWorkfileCreate(NukeLocalSyntheticTestClass):
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
        ("1SUurHj2aiQ21ZIMJfGVBI2KjR8kIjBGI", "test_Nuke_publish.zip", "")
    ]

    APP_GROUP = "nuke"

    TIMEOUT = 50  # publish timeout

    # could be overwritten by command line arguments
    # keep empty to locate latest installed variant or explicit
    APP_VARIANT = ""
    PERSIST = True  # True - keep test_db, test_openpype, outputted test files
    TEST_DATA_FOLDER = r"C:\CODE\__PYPE\__unit_testing_data\test_nuke_workfile"

    def test_workfile_created(self, last_workfile_path):

        """Host and input data dependent expected results in DB."""
        print("Test last workfile path: {}".format(last_workfile_path))
        failures = []

        assert not any(failures)


if __name__ == "__main__":
    test_case = TestWorkfileCreate()
