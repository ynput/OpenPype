import re
import os
import json
from collections import defaultdict

from tests.integration.hosts.maya.lib import MayaLocalPublishTestClass


class TestPublishInMaya(MayaLocalPublishTestClass):
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
        ("test_publish_in_maya", "", "")
    ]

    APP_GROUP = "maya"
    # keep empty to locate latest installed variant or explicit
    APP_VARIANT = ""

    TIMEOUT = 120  # publish timeout

    def test_publish(
        self,
        dbcon,
        publish_finished,
        download_test_data
    ):
        """Testing Pyblish and Python logs within Maya."""

        # All maya output via MAYA_CMD_FILE_OUTPUT env var during test run
        logging_path = os.path.join(download_test_data, "output.log")
        with open(logging_path, "r") as f:
            logging_output = f.read()

        print(("-" * 50) + "LOGGING" + ("-" * 50))
        print(logging_output)

        # Check for pyblish errors.
        error_regex = r"pyblish \(ERROR\)((.|\n)*?)((pyblish \())"
        matches = re.findall(error_regex, logging_output)
        assert not matches, matches[0][0]

        # Check for python errors.
        error_regex = r"// Error((.|\n)*)"
        matches = re.findall(error_regex, logging_output)
        assert not matches, matches[0][0]

    def count_of_types(self, dbcon, queried_type, **kwargs):
        """Queries 'dbcon' and counts documents of type 'queried_type'

            Args:
                dbcon (AvalonMongoDB)
                queried_type (str): type of document ("asset", "version"...)
                expected (int): number of documents found
                any number of additional keyword arguments

                special handling of argument additional_args (dict)
                    with additional args like
                    {"context.subset": "XXX"}
        """
        args = {"type": queried_type}
        for key, val in kwargs.items():
            if key == "additional_args":
                args.update(val)
            else:
                args[key] = val

        return dbcon.count_documents(args)

    def test_db_asserts(self, dbcon, publish_finished, download_test_data):
        """Host and input data dependent expected results in DB."""

        expected_data = None
        json_path = os.path.join(
            download_test_data,
            "expected",
            "dumps",
            "avalon_tests.test_project.json"
        )
        with open(json_path, "r") as f:
            expected_data = json.load(f)

        expected_entities = {
            "subset": [],
            "version": [],
            "representation": [],
            "hero_version": []
        }
        for entity in expected_data:
            if entity["type"] in expected_entities.keys():
                expected_entities[entity["type"]].append(entity)

        asserts = []

        # Ensure entities amount is correct.
        for entity_type, entities in expected_entities.items():
            current = self.count_of_types(dbcon, entity_type)
            expected = len(entities)
            msg = (
                "{} count is not the same as expected. Current: {}."
                " Expected: {}.".format(entity_type, current, expected)
            )
            if current != expected:
                asserts.append(msg)

        # Ensure there is only 1 version of each subset.
        current = self.count_of_types(dbcon, "version", name={"$ne": 1})
        expected = 0
        msg = (
            "Found versions that are not the first (1) version. Only one"
            " version per subset expected."
        )
        if current != expected:
            asserts.append(msg)

        # Ensure names of subset entities are the same.
        subset_names = [x["name"] for x in expected_entities["subset"]]
        for name in subset_names:
            current = self.count_of_types(
                dbcon, entity_type, type="subset", name=name
            )
            msg = "Subset with name \"{}\" was not found.".format(name)
            if current != 1:
                asserts.append(msg)

        # Ensure correct amount of representations by their context.
        context_keys = [
            "asset",
            "family",
            "subset",
            "ext",
            "representation",
        ]
        temp = []
        representation_contexts = defaultdict(list)
        for entity in expected_entities["representation"]:
            context = {}
            for key in context_keys:
                context["context." + key] = entity["context"][key]

            index = len(temp)
            if context in temp:
                index = temp.index(context)
            else:
                temp.append(context)

            representation_contexts[index].append(context)

        for _, contexts in representation_contexts.items():
            context = contexts[0]
            current = self.count_of_types(
                dbcon, "representation", additional_args=context
            )
            expected = len(contexts)
            msg = (
                "Representation(s) with context as below was not found."
                " Current: {}."
                " Expected: {}.\n{}".format(current, expected, context)
            )
            if current != expected:
                asserts.append(msg)

        assert asserts == [], "\n".join(asserts)


if __name__ == "__main__":
    test_case = TestPublishInMaya()
