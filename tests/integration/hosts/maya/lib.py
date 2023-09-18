import os
import shutil
import re

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
            args = ["-I", self.get_usersetup_path()]

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


class MayaPublishTest(MayaFixtures, PublishTest):
    """Testing class for local publishes."""
