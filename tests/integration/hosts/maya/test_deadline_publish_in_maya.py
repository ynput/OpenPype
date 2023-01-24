from tests.lib.assert_classes import DBAssert
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
    PERSIST = True

    TEST_FILES = [
        ("1dDY7CbdFXfRksGVoiuwjhnPoTRCCf5ea",
         "test_maya_deadline_publish.zip", "")
    ]

    APP_GROUP = "maya"
    # keep empty to locate latest installed variant or explicit
    APP_VARIANT = ""

    TIMEOUT = 120  # publish timeout

    def test_db_asserts(self, dbcon, publish_finished):
        """Host and input data dependent expected results in DB."""
        print("test_db_asserts")
        failures = []
        failures.append(DBAssert.count_of_types(dbcon, "version", 3))

        failures.append(
            DBAssert.count_of_types(dbcon, "version", 0, name={"$ne": 1}))

        failures.append(
            DBAssert.count_of_types(dbcon, "subset", 1,
                                    name="modelMain"))

        failures.append(
            DBAssert.count_of_types(dbcon, "subset", 1,
                                    name="renderTest_taskMain_beauty"))

        failures.append(
            DBAssert.count_of_types(dbcon, "subset", 1,
                                    name="workfileTest_task"))

        failures.append(DBAssert.count_of_types(dbcon, "representation", 8))

        # hero included
        additional_args = {"context.subset": "modelMain",
                           "context.ext": "abc"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 2,
                                    additional_args=additional_args))

        # hero included
        additional_args = {"context.subset": "modelMain",
                           "context.ext": "ma"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 2,
                                    additional_args=additional_args))

        additional_args = {"context.subset": "modelMain",
                           "context.ext": "mb"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 0,
                                    additional_args=additional_args))

        additional_args = {"context.subset": "renderTest_taskMain_beauty",
                           "context.ext": "exr"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 1,
                                    additional_args=additional_args))

        additional_args = {"context.subset": "renderTest_taskMain_beauty",
                           "context.ext": "jpg"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 1,
                                    additional_args=additional_args))

        additional_args = {"context.subset": "renderTest_taskMain_beauty",
                           "context.ext": "png"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 1,
                                    additional_args=additional_args))

        assert not any(failures)


if __name__ == "__main__":
    test_case = TestDeadlinePublishInMaya()
