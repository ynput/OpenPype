from tests.integration.hosts.maya.lib import MayaTestClass


class TestPublishInMaya(MayaTestClass):
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
        ("1BTSIIULJTuDc8VvXseuiJV_fL6-Bu7FP", "test_maya_publish.zip", "")
    ]

    APP = "maya"
    # keep empty to locate latest installed variant or explicit
    APP_VARIANT = ""

    TIMEOUT = 120  # publish timeout

    def test_db_asserts(self, dbcon, publish_finished):
        """Host and input data dependent expected results in DB."""
        print("test_db_asserts")
        assert 5 == dbcon.count_documents({"type": "version"}), \
            "Not expected no of versions"

        assert 0 == dbcon.count_documents({"type": "version",
                                           "name": {"$ne": 1}}), \
            "Only versions with 1 expected"

        assert 1 == dbcon.count_documents({"type": "subset",
                                           "name": "modelMain"}), \
            "modelMain subset must be present"

        assert 1 == dbcon.count_documents({"type": "subset",
                                           "name": "workfileTest_task"}), \
            "workfileTest_task subset must be present"

        assert 11 == dbcon.count_documents({"type": "representation"}), \
            "Not expected no of representations"

        assert 2 == dbcon.count_documents({"type": "representation",
                                           "context.subset": "modelMain",
                                           "context.ext": "abc"}), \
            "Not expected no of representations with ext 'abc'"

        assert 2 == dbcon.count_documents({"type": "representation",
                                           "context.subset": "modelMain",
                                           "context.ext": "ma"}), \
            "Not expected no of representations with ext 'abc'"


if __name__ == "__main__":
    test_case = TestPublishInMaya()
