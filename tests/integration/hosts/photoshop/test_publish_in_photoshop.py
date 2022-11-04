import logging

from tests.lib.assert_classes import DBAssert
from tests.integration.hosts.photoshop.lib import PhotoshopTestClass

log = logging.getLogger("test_publish_in_photoshop")


class TestPublishInPhotoshop(PhotoshopTestClass):
    """Basic test case for publishing in Photoshop

        Uses generic TestCase to prepare fixtures for test data, testing DBs,
        env vars.

        Opens Photoshop, run publish on prepared workile.

        Test zip file sets 3 required env vars:
        - HEADLESS_PUBLISH - this triggers publish immediately app is open
        - IS_TEST - this differentiate between regular webpublish
        - PYBLISH_TARGETS

        Always pulls and uses test data from GDrive!

        Test zip file sets 3 required env vars:
        - HEADLESS_PUBLISH - this triggers publish immediately app is open
        - IS_TEST - this differentiate between regular webpublish
        - PYBLISH_TARGETS

        Then checks content of DB (if subset, version, representations were
        created.
        Checks tmp folder if all expected files were published.

        How to run:
        (in cmd with activated {OPENPYPE_ROOT}/.venv)
        {OPENPYPE_ROOT}/.venv/Scripts/python.exe {OPENPYPE_ROOT}/start.py runtests ../tests/integration/hosts/photoshop  # noqa: E501

    """
    PERSIST = True

    TEST_FILES = [
        ("1zD2v5cBgkyOm_xIgKz3WKn8aFB_j8qC-", "test_photoshop_publish.zip", "")
    ]

    APP_GROUP = "photoshop"
    # keep empty to locate latest installed variant or explicit
    APP_VARIANT = ""

    APP_NAME = "{}/{}".format(APP_GROUP, APP_VARIANT)

    TIMEOUT = 120  # publish timeout

    def test_db_asserts(self, dbcon, publish_finished):
        """Host and input data dependent expected results in DB."""
        print("test_db_asserts")
        failures = []

        failures.append(DBAssert.count_of_types(dbcon, "version", 4))

        failures.append(
            DBAssert.count_of_types(dbcon, "version", 0, name={"$ne": 1}))

        failures.append(
            DBAssert.count_of_types(dbcon, "subset", 1,
                                    name="imageMainForeground"))

        failures.append(
            DBAssert.count_of_types(dbcon, "subset", 1,
                                    name="imageMainBackground"))

        failures.append(
            DBAssert.count_of_types(dbcon, "subset", 1,
                                    name="workfileTest_task"))

        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 6))

        additional_args = {"context.subset": "imageMainForeground",
                           "context.ext": "png"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 1,
                                    additional_args=additional_args))

        additional_args = {"context.subset": "imageMainForeground",
                           "context.ext": "jpg"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 1,
                                    additional_args=additional_args))

        additional_args = {"context.subset": "imageMainBackground",
                           "context.ext": "png"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 1,
                                    additional_args=additional_args))

        additional_args = {"context.subset": "imageMainBackground",
                           "context.ext": "jpg"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 1,
                                    additional_args=additional_args))

        assert not any(failures)


if __name__ == "__main__":
    test_case = TestPublishInPhotoshop()
