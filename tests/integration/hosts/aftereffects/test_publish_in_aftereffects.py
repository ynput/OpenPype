import logging

from tests.lib.assert_classes import DBAssert
from tests.integration.hosts.aftereffects.lib import AELocalPublishTestClass

log = logging.getLogger("test_publish_in_aftereffects")


class TestPublishInAfterEffects(AELocalPublishTestClass):
    """Basic test case for publishing in AfterEffects

        Uses generic TestCase to prepare fixtures for test data, testing DBs,
        env vars.

        Opens AfterEffects, run publish on prepared workile.

        Test zip file sets 3 required env vars:
        - HEADLESS_PUBLISH - this triggers publish immediately app is open
        - IS_TEST - this differentiate between regular webpublish
        - PYBLISH_TARGETS

        Then checks content of DB (if subset, version, representations were
        created.
        Checks tmp folder if all expected files were published.

    """
    PERSIST = False

    TEST_FILES = [
        ("1c8261CmHwyMgS-g7S4xL5epAp0jCBmhf",
         "test_aftereffects_publish.zip",
         "")
    ]

    APP_GROUP = "aftereffects"
    APP_VARIANT = ""

    APP_NAME = "{}/{}".format(APP_GROUP, APP_VARIANT)

    TIMEOUT = 120  # publish timeout

    def test_db_asserts(self, dbcon, publish_finished):
        """Host and input data dependent expected results in DB."""
        print("test_db_asserts")
        failures = []

        failures.append(DBAssert.count_of_types(dbcon, "version", 2))

        failures.append(
            DBAssert.count_of_types(dbcon, "version", 0, name={"$ne": 1}))

        failures.append(
            DBAssert.count_of_types(dbcon, "subset", 1,
                                    name="workfileTest_task"))

        failures.append(
            DBAssert.count_of_types(dbcon, "subset", 1,
                                    name="renderTest_taskMain"))

        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 4))

        additional_args = {"context.subset": "workfileTest_task",
                           "context.ext": "aep"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 1,
                                    additional_args=additional_args))

        additional_args = {"context.subset": "renderTest_taskMain",
                           "context.ext": "png"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 2,
                                    additional_args=additional_args))

        additional_args = {"context.subset": "renderTest_taskMain",
                           "name": "thumbnail"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 1,
                                    additional_args=additional_args))

        additional_args = {"context.subset": "renderTest_taskMain",
                           "name": "png_png"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 1,
                                    additional_args=additional_args))

        assert not any(failures)


if __name__ == "__main__":
    test_case = TestPublishInAfterEffects()
