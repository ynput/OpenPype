import os

from tests.lib.assert_classes import DBAssert
from tests.integration.hosts.maya.lib import MayaPublishTest


class TestPublishInMaya(MayaPublishTest):
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

    INPUT_DUMPS = os.path.join(
        os.path.dirname(__file__), "input", "dumps"
    )
    INPUT_ENVIRONMENT_JSON = os.path.join(
        os.path.dirname(__file__), "input", "env_vars", "env_var.json"
    )
    INPUT_WORKFILE = os.path.join(
        os.path.dirname(__file__), "input", "workfile"
    )

    FILES = [
        ("1BTSIIULJTuDc8VvXseuiJV_fL6-Bu7FP", "test_maya_publish.zip", "")
    ]

    def test_db_asserts(self, dbcon, deadline_finished):
        """Host and input data dependent expected results in DB."""
        print("test_db_asserts")
        asserts = []
        asserts.append(DBAssert.count_of_types(dbcon, "version", 3))

        asserts.append(
            DBAssert.count_of_types(dbcon, "version", 0, name={"$ne": 1})
        )

        asserts.append(
            DBAssert.count_of_types(dbcon, "subset", 1, name="modelMain")
        )

        asserts.append(
            DBAssert.count_of_types(
                dbcon, "subset", 1, name="workfileTest_task"
            )
        )

        asserts.append(DBAssert.count_of_types(dbcon, "representation", 8))

        asserts.append(
            DBAssert.count_of_types(
                dbcon,
                "representation",
                2,
                additional_args={
                    "context.subset": "modelMain", "context.ext": "abc"
                }
            )
        )

        asserts.append(
            DBAssert.count_of_types(
                dbcon,
                "representation",
                2,
                additional_args={
                    "context.subset": "modelMain", "context.ext": "ma"
                }
            )
        )

        asserts.append(
            DBAssert.count_of_types(
                dbcon,
                "representation",
                1,
                additional_args={
                    "context.subset": "workfileTest_task", "context.ext": "ma"
                }
            )
        )

        asserts.append(
            DBAssert.count_of_types(
                dbcon, "subset", 1, name="renderTest_taskRenderMain_beauty"
            )
        )

        asserts.append(
            DBAssert.count_of_types(
                dbcon,
                "representation",
                1,
                additional_args={
                    "context.subset": "renderTest_taskRenderMain_beauty",
                    "context.ext": "exr"
                }
            )
        )

        asserts.append(
            DBAssert.count_of_types(
                dbcon,
                "representation",
                1,
                additional_args={
                    "context.subset": "renderTest_taskRenderMain_beauty",
                    "context.ext": "jpg"
                }
            )
        )

        asserts.append(
            DBAssert.count_of_types(
                dbcon,
                "representation",
                1,
                additional_args={
                    "context.subset": "renderTest_taskRenderMain_beauty",
                    "context.ext": "png"
                }
            )
        )

        failures = [x for x in asserts if x is not None]
        msg = "Failures:\n" + "\n".join(failures)
        assert not failures, msg


if __name__ == "__main__":
    test_case = TestPublishInMaya()
