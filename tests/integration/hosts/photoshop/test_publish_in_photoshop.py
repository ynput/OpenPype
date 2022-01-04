from tests.integration.hosts.photoshop.lib import PhotoshopTestClass


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
    PERSIST = False

    TEST_FILES = [
        ("1zD2v5cBgkyOm_xIgKz3WKn8aFB_j8qC-", "test_photoshop_publish.zip", "")
    ]

    APP = "photoshop"
    # keep empty to locate latest installed variant or explicit
    APP_VARIANT = ""

    APP_NAME = "{}/{}".format(APP, APP_VARIANT)

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
                                           "name": "imageMainBackgroundcopy"}
                                          ), \
            "modelMain subset must be present"

        assert 1 == dbcon.count_documents({"type": "subset",
                                           "name": "workfileTesttask"}), \
            "workfileTest_task subset must be present"

        assert 6 == dbcon.count_documents({"type": "representation"}), \
            "Not expected no of representations"

        assert 1 == dbcon.count_documents({"type": "representation",
                                           "context.subset": "imageMainBackgroundcopy",  # noqa: E501
                                           "context.ext": "png"}), \
            "Not expected no of representations with ext 'png'"


if __name__ == "__main__":
    test_case = TestPublishInPhotoshop()
