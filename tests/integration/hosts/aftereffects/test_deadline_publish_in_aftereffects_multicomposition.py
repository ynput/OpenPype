import logging

from tests.lib.assert_classes import DBAssert
from tests.integration.hosts.aftereffects.lib import AEDeadlinePublishTestClass

log = logging.getLogger("test_publish_in_aftereffects")


class TestDeadlinePublishInAfterEffectsMultiComposition(AEDeadlinePublishTestClass):  # noqa
    """est case for DL publishing in AfterEffects with multiple compositions.

        Workfile contains 2 prepared `render` instances. First has review set,
        second doesn't.

        Uses generic TestCase to prepare fixtures for test data, testing DBs,
        env vars.

        Opens AfterEffects, run DL publish on prepared workile.

        Test zip file sets 3 required env vars:
        - HEADLESS_PUBLISH - this triggers publish immediately app is open
        - IS_TEST - this differentiate between regular webpublish
        - PYBLISH_TARGETS

        As there are multiple render and publish jobs, it waits for publish job
        of later render job. Depends on date created of metadata.json.

        Then checks content of DB (if subset, version, representations were
        created.
        Checks tmp folder if all expected files were published.

    """
    PERSIST = False

    TEST_FILES = [
        ("16xIm3U5P7WQJXpa9E06jWebMK9QKUATN",
         "test_aftereffects_deadline_publish_multicomposition.zip",
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

        failures.append(DBAssert.count_of_types(dbcon, "version", 3))

        failures.append(
            DBAssert.count_of_types(dbcon, "version", 0, name={"$ne": 1}))

        failures.append(
            DBAssert.count_of_types(dbcon, "subset", 3))

        failures.append(
            DBAssert.count_of_types(dbcon, "subset", 1,
                                    name="workfileTest_task"))

        failures.append(
            DBAssert.count_of_types(dbcon, "subset", 1,
                                    name="renderTest_taskMain"))

        failures.append(
            DBAssert.count_of_types(dbcon, "subset", 1,
                                    name="renderTest_taskMain2"))

        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 5))

        additional_args = {"context.subset": "workfileTest_task",
                           "context.ext": "aep"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 1,
                                    additional_args=additional_args))

        # renderTest_taskMain
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

        # renderTest_taskMain2
        additional_args = {"context.subset": "renderTest_taskMain2",
                           "context.ext": "exr"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 1,
                                    additional_args=additional_args))

        additional_args = {"context.subset": "renderTest_taskMain2",
                           "name": "thumbnail"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 0,
                                    additional_args=additional_args))

        additional_args = {"context.subset": "renderTest_taskMain2",
                           "name": "png_exr"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 0,
                                    additional_args=additional_args))

        assert not any(failures)


if __name__ == "__main__":
    test_case = TestDeadlinePublishInAfterEffectsMultiComposition()
