import os
import pytest
import re

from tests.lib.testing_classes import ModuleUnitTest
from tests.lib.testing_classes import (
    HostFixtures,
    PublishTest,
    AppLaunchTest,
    DeadlinePublishTest
)
from openpype.lib.local_settings import get_openpype_username
from openpype.pipeline.workfile import (
    get_workfile_template_key,
    get_last_workfile,
    get_workdir_with_workdir_data
)
from openpype.pipeline import HOST_WORKFILE_EXTENSIONS
from openpype.pipeline.template_data import get_template_data


class NukeStaticTestHostFixtures(HostFixtures):
    @pytest.fixture(scope="module")
    def last_workfile_path(self, download_test_data, output_folder_url):
        """Get last_workfile_path from source data.

        """
        source_file_name = "test_project_test_asset_test_task_v001.nk"
        src_path = os.path.join(download_test_data,
                                "input",
                                "workfile",
                                source_file_name)
        dest_folder = os.path.join(output_folder_url,
                                   self.PROJECT,
                                   self.ASSET,
                                   "work",
                                   self.TASK)
        if not os.path.exists(dest_folder):
            os.makedirs(dest_folder)

        dest_path = os.path.join(dest_folder,
                                 source_file_name)

        # rewrite old root with temporary file
        # TODO - using only C:/projects seems wrong - but where to get root ?
        replace_pattern = re.compile(re.escape("C:/projects"), re.IGNORECASE)
        with open(src_path, "r") as fp:
            updated = fp.read()
            updated = replace_pattern.sub(output_folder_url.replace("\\", '/'),
                                          updated)

        with open(dest_path, "w") as fp:
            fp.write(updated)

        yield dest_path

    @pytest.fixture(scope="module")
    def startup_scripts(self, monkeypatch_session, download_test_data):
        """Points Nuke to userSetup file from input data"""
        startup_path = os.path.join(download_test_data,
                                    "input",
                                    "startup")
        original_nuke_path = os.environ.get("NUKE_PATH", "")
        monkeypatch_session.setenv("NUKE_PATH",
                                   "{}{}{}".format(startup_path,
                                                   os.pathsep,
                                                   original_nuke_path))

    @pytest.fixture(scope="module")
    def skip_compare_folders(self):
        yield []


class NukeSyntheticHostFixtures(NukeStaticTestHostFixtures, ModuleUnitTest):

    @pytest.fixture(scope="module")
    def last_workfile_path(
        self, project_settings, project_anatomy,
        system_settings, project_doc, asset_doc
    ):
        """Get last_workfile_path from source data.

        """
        host_name = "nuke"
        extensions = HOST_WORKFILE_EXTENSIONS.get(host_name)
        anatomy = project_anatomy

        workdir_data = get_template_data(
            project_doc, asset_doc, self.TASK, host_name, system_settings
        )

        workdir = get_workdir_with_workdir_data(
            workdir_data,
            anatomy.project_name,
            anatomy,
            project_settings=project_settings
        )

        project_settings = project_settings
        task_type = workdir_data["task"]["type"]
        template_key = get_workfile_template_key(
            task_type,
            host_name,
            self.PROJECT,
            project_settings=project_settings
        )
        # Find last workfile
        file_template = str(anatomy.templates[template_key]["file"])

        workdir_data.update({
            "version": 1,
            "user": get_openpype_username(),
            "ext": extensions[0]
        })

        last_workfile_path = get_last_workfile(
            workdir, file_template, workdir_data, extensions, True
        )

        yield last_workfile_path


class NukeLocalSyntheticTestClass(NukeSyntheticHostFixtures, AppLaunchTest):
    """Testing class for local publishes."""


class NukeLocalPublishTestClass(NukeStaticTestHostFixtures, PublishTest):
    """Testing class for local publishes."""


class NukeDeadlinePublishTestClass(
    NukeStaticTestHostFixtures, DeadlinePublishTest
):
    """Testing class for Deadline publishes."""
