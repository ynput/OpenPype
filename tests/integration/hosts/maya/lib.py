import os
import pytest
import shutil
import json
from collections import defaultdict

from tests.lib.testing_classes import (
    HostFixtures,
    PublishTest,
    DeadlinePublishTest
)


class MayaHostFixtures(HostFixtures):
    @pytest.fixture(scope="module")
    def last_workfile_path(self, download_test_data, output_folder_url):
        """Get last_workfile_path from source data.

            Maya expects workfile in proper folder, so copy is done first.
        """
        src_path = os.path.join(
            download_test_data,
            "input",
            "workfile",
            "test_project_test_asset_test_task_v001.ma"
        )
        dest_folder = os.path.join(
            output_folder_url,
            self.PROJECT,
            self.ASSET,
            "work",
            self.TASK
        )

        os.makedirs(dest_folder)

        dest_path = os.path.join(
            dest_folder, "test_project_test_asset_test_task_v001.ma"
        )
        shutil.copy(src_path, dest_path)

        yield dest_path

    @pytest.fixture(scope="module")
    def startup_scripts(self, monkeypatch_session, download_test_data):
        """Points Maya to userSetup file from input data"""
        startup_path = os.path.join(
            download_test_data, "input", "startup"
        )
        original_pythonpath = os.environ.get("PYTHONPATH")
        monkeypatch_session.setenv(
            "PYTHONPATH",
            "{}{}{}".format(startup_path, os.pathsep, original_pythonpath)
        )

        monkeypatch_session.setenv(
            "MAYA_CMD_FILE_OUTPUT",
            os.path.join(download_test_data, "output.log")
        )

    @pytest.fixture(scope="module")
    def skip_compare_folders(self):
        yield []

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


class MayaLocalPublishTestClass(MayaHostFixtures, PublishTest):
    """Testing class for local publishes."""


class MayaDeadlinePublishTestClass(MayaHostFixtures, DeadlinePublishTest):
    """Testing class for Deadline publishes."""
