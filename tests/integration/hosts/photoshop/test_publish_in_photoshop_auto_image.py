import logging

from tests.lib.assert_classes import DBAssert
from tests.integration.hosts.photoshop.lib import PhotoshopTestClass

log = logging.getLogger("test_publish_in_photoshop")


class TestPublishInPhotoshopAutoImage(PhotoshopTestClass):
    """Test for publish in Phohoshop with different review configuration.

    Workfile contains 3 layers, auto image and review instances created.

    Test contains updates to Settings!!!

    """
    PERSIST = True

    TEST_FILES = [
        ("1iLF6aNI31qlUCD1rGg9X9eMieZzxL-rc",
         "test_photoshop_publish_auto_image.zip", "")
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

        failures.append(DBAssert.count_of_types(dbcon, "version", 3))

        failures.append(
            DBAssert.count_of_types(dbcon, "version", 0, name={"$ne": 1}))

        failures.append(
            DBAssert.count_of_types(dbcon, "subset", 0,
                                    name="imageMainForeground"))

        failures.append(
            DBAssert.count_of_types(dbcon, "subset", 0,
                                    name="imageMainBackground"))

        failures.append(
            DBAssert.count_of_types(dbcon, "subset", 1,
                                    name="workfileTest_task"))

        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 5))

        additional_args = {"context.subset": "imageMainForeground",
                           "context.ext": "png"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 0,
                                    additional_args=additional_args))

        additional_args = {"context.subset": "imageMainBackground",
                           "context.ext": "png"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 0,
                                    additional_args=additional_args))

        # review from image
        additional_args = {"context.subset": "imageBeautyMain",
                           "context.ext": "jpg",
                           "name": "jpg_jpg"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 1,
                                    additional_args=additional_args))

        additional_args = {"context.subset": "imageBeautyMain",
                           "context.ext": "jpg",
                           "name": "jpg"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 1,
                                    additional_args=additional_args))

        additional_args = {"context.subset": "review"}
        failures.append(
            DBAssert.count_of_types(dbcon, "representation", 1,
                                    additional_args=additional_args))

        assert not any(failures)


if __name__ == "__main__":
    test_case = TestPublishInPhotoshopAutoImage()
