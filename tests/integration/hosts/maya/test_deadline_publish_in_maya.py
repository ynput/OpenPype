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
        ("test_deadline_publish_in_maya", "", "")
    ]

    APP_GROUP = "maya"
    # keep empty to locate latest installed variant or explicit
    APP_VARIANT = ""

    TIMEOUT = 180  # publish timeout


if __name__ == "__main__":
    test_case = TestDeadlinePublishInMaya()
