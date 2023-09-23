import os
import shutil
import re
import json
from collections import defaultdict

import pytest

from tests.lib.testing_classes import HostFixtures, PublishTest


class MayaFixtures(HostFixtures):

    # By default run through mayapy. For interactive mode, change to "maya" or
    # input `--app_group maya` in cli.
    APP_GROUP = "mayapy"

    def running_in_mayapy(self, app_group):
        app_group = app_group or self.APP_GROUP

        # Running in mayapy.
        if app_group == "mayapy":
            return True

        # Running in maya.
        return False

    def get_usersetup_path(self):
        return os.path.join(
            os.path.dirname(__file__), "input", "startup", "userSetup.py"
        )

    def get_log_path(self, dirpath, app_variant):
        return os.path.join(
            dirpath, "output_{}.log".format(app_variant)
        )

    @pytest.fixture(scope="module")
    def app_args(self, app_group, app_variant):
        args = []

        if self.running_in_mayapy(app_group):
            # Attempts to run MayaPy in 2022 has failed.
            msg = "Maya 2022 and older is not supported through MayaPy"
            assert int(app_variant) > 2022, msg

            # Maya 2023+ can isolate from the users environment. Although the
            # command flag is present in older versions of Maya, it does not
            # work resulting a fatal python error:
            # Fatal Python error: initfsencoding: unable to load the file
            #    system codec
            # ModuleNotFoundError: No module named 'encodings'
            args.append("-I")

            # MayaPy can only be passed a python script, so Maya scene opening
            # will happen post launch.
            args.append(self.get_usersetup_path())

        yield args

    @pytest.fixture(scope="module")
    def start_last_workfile(self, app_group):
        """Returns url of workfile"""
        return not self.running_in_mayapy(app_group)

    @pytest.fixture(scope="module")
    def last_workfile_path(self, setup_fixture):
        """Get last_workfile_path from source data.

            Maya expects workfile in proper folder, so copy is done first.
        """
        data_folder, output_folder, _ = setup_fixture

        source_folder = (
            self.INPUT_WORKFILE or
            os.path.join(data_folder, "input", "workfile")
        )
        filename = os.listdir(source_folder)[0]
        src_path = os.path.join(source_folder, filename)
        dest_folder = os.path.join(
            output_folder,
            self.PROJECT_NAME,
            self.ASSET_NAME,
            "work",
            self.TASK_NAME
        )
        os.makedirs(dest_folder)
        dest_path = os.path.join(dest_folder, filename)
        shutil.copy(src_path, dest_path)

        yield dest_path

    @pytest.fixture(scope="module")
    def startup_scripts(
        self, monkeypatch_session, setup_fixture, app_group, app_variant
    ):
        data_folder, _, _ = setup_fixture

        """Points Maya to userSetup file from input data"""
        if not self.running_in_mayapy(app_group):
            # Not needed for running MayaPy since the testing userSetup.py will
            # be passed in directly to the executable.
            original_pythonpath = os.environ.get("PYTHONPATH")
            monkeypatch_session.setenv(
                "PYTHONPATH",
                "{}{}{}".format(
                    os.path.dirname(self.get_usersetup_path()),
                    os.pathsep,
                    original_pythonpath
                )
            )

        monkeypatch_session.setenv(
            "MAYA_CMD_FILE_OUTPUT",
            self.get_log_path(data_folder, app_variant)
        )

    @pytest.fixture(scope="module")
    def skip_compare_folders(self):
        pass


class TestPublishInMaya(MayaFixtures, PublishTest):
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

    EXPECTED_FOLDER = os.path.join(
        os.path.dirname(__file__), "expected", "files"
    )
    INPUT_DUMPS = os.path.join(os.path.dirname(__file__), "input", "dumps")
    INPUT_ENVIRONMENT_JSON = os.path.join(
        os.path.dirname(__file__), "input", "env_vars", "env_var.json"
    )
    INPUT_WORKFILE = os.path.join(
        os.path.dirname(__file__), "input", "workfile"
    )

    FILES = []

    def test_publish(
        self,
        dbcon,
        publish_finished,
        setup_fixture,
        app_variant
    ):
        data_folder, _, _ = setup_fixture

        logging_path = self.get_log_path(data_folder, app_variant)
        with open(logging_path, "r") as f:
            logging_output = f.read()

        print(("-" * 50) + "LOGGING" + ("-" * 50))
        print(logging_output)
        print(("-" * 50) + "PUBLISH" + ("-" * 50))
        print(publish_finished)

        # Check for pyblish errors.
        error_regex = r"pyblish \(ERROR\)((.|\n)*?)((pyblish \())"
        matches = re.findall(error_regex, logging_output)
        assert not matches, matches[0][0]

        matches = re.findall(error_regex, publish_finished)
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

    def test_db_asserts(self, dbcon, deadline_finished):
        """Host and input data dependent expected results in DB."""

        expected_data = None
        json_path = os.path.join(
            os.path.dirname(__file__),
            "expected",
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

        for entity_type, entities in expected_entities.items():
            # Ensure entity counts are correct.
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
