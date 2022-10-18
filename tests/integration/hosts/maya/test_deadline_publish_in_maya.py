from tests.integration.hosts.maya.lib import MayaDeadlinePublishTestClass


class TestDeadlinePublishInMaya(MayaDeadlinePublishTestClass):
    """Basic test case for publishing in Maya


        Always pulls and uses test data from GDrive!

        Opens Maya, runs publish on prepared workile.

        Sends file to be rendered on Deadline.

        Then checks content of DB (if subset, version, representations were
        created.
        Checks tmp folder if all expected files were published.

        How to run:
        (in cmd with activated {OPENPYPE_ROOT}/.venv)
        {OPENPYPE_ROOT}/.venv/Scripts/python.exe {OPENPYPE_ROOT}/start.py runtests ../tests/integration/hosts/maya  # noqa: E501

    """
    PERSIST = False

    TEST_FILES = [
        ("1dDY7CbdFXfRksGVoiuwjhnPoTRCCf5ea",
         "test_maya_deadline_publish.zip", "")
    ]

    APP = "maya"
    # keep empty to locate latest installed variant or explicit
    APP_VARIANT = ""

    TIMEOUT = 120  # publish timeout

    def test_db_asserts(self, dbcon, publish_finished):
        """Host and input data dependent expected results in DB."""
        print("test_db_asserts")
        assert 3 == dbcon.count_documents({"type": "version"}), \
            "Not expected no of versions"

        assert 0 == dbcon.count_documents({"type": "version",
                                           "name": {"$ne": 1}}), \
            "Only versions with 1 expected"

        assert 1 == dbcon.count_documents({"type": "subset",
                                           "name": "modelMain"}), \
            "modelMain subset must be present"

        assert 1 == dbcon.count_documents({
            "type": "subset", "name": "renderTestTaskMain_beauty"}), \
            "renderTestTaskMain_beauty subset must be present"

        assert 1 == dbcon.count_documents({"type": "subset",
                                           "name": "workfileTesttask"}), \
            "workfileTesttask subset must be present"

        assert 6 == dbcon.count_documents({"type": "representation"}), \
            "Not expected no of representations"

        assert 1 == dbcon.count_documents({"type": "representation",
                                           "context.subset": "modelMain",
                                           "context.ext": "abc"}), \
            "Not expected no of representations with ext 'abc'"

        assert 1 == dbcon.count_documents({"type": "representation",
                                           "context.subset": "modelMain",
                                           "context.ext": "ma"}), \
            "Not expected no of representations with ext 'ma'"

        assert 1 == dbcon.count_documents({"type": "representation",
                                           "context.subset": "workfileTesttask",  # noqa
                                           "context.ext": "mb"}), \
            "Not expected no of representations with ext 'mb'"

        assert 1 == dbcon.count_documents({"type": "representation",
                                           "context.subset": "renderTestTaskMain_beauty",  # noqa
                                           "context.ext": "exr"}), \
            "Not expected no of representations with ext 'exr'"

        assert 1 == dbcon.count_documents({"type": "representation",
                                           "context.subset": "renderTestTaskMain_beauty",  # noqa
                                           "context.ext": "jpg"}), \
            "Not expected no of representations with ext 'jpg'"

        assert 1 == dbcon.count_documents({"type": "representation",
                                           "context.subset": "renderTestTaskMain_beauty",  # noqa
                                           "context.ext": "h264_exr"}), \
            "Not expected no of representations with ext 'h264_exr'"


if __name__ == "__main__":
    test_case = TestDeadlinePublishInMaya()
