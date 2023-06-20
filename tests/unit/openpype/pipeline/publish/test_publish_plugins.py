

"""Test Publish_plugins pipeline publish modul, tests API methods

    File:
        creates temporary directory and downloads .zip file from GDrive
        unzips .zip file
        uses content of .zip file (MongoDB's dumps) to import to new databases
        with use of 'monkeypatch_session' modifies required env vars
            temporarily
        runs battery of tests checking that site operation for Sync Server
            module are working
        removes temporary folder
        removes temporary databases (?)
"""
import os
import pytest
import shutil
import logging

from tests.unit.openpype.pipeline.lib import TestPipeline
from openpype.pipeline.publish import publish_plugins
from openpype.pipeline import colorspace

log = logging.getLogger(__name__)


class TestPipelinePublishPlugins(TestPipeline):
    """ Testing Pipeline publish_plugins.py

    Example:
        cd to OpenPype repo root dir
        poetry run python ./start.py runtests \
            ../tests/unit/openpype/pipeline/publish
    """

    # files are the same as those used in `test_pipeline_colorspace`
    TEST_FILES = [
        (
            "1Lf-mFxev7xiwZCWfImlRcw7Fj8XgNQMh",
            "test_pipeline_colorspace.zip",
            ""
        )
    ]
    PROJECT = "test_project"
    ASSET = "sh0010"
    HIERARCHY = "shots/sq010"
    TASK = "comp"

    @pytest.fixture(scope="module")
    def context(self, legacy_io, project_settings):
        class CTX:
            data = {
                "projectName": legacy_io["AVALON_PROJECT"],
                "asset": legacy_io["AVALON_ASSET"],
                "hostName": "nuke",
                "anatomyData": {},
                "project_settings": project_settings
            }
        yield CTX

    @pytest.fixture(scope="module")
    def config_path_project(
        self,
        download_test_data,
        output_folder_url
    ):
        src_path = os.path.join(
            download_test_data,
            "input",
            "data",
            "configs",
            "aces_1.3",
            "ayon_aces_config_project.ocio"
        )
        dest_dir = os.path.join(
            output_folder_url,
            self.PROJECT,
            "config"
        )
        dest_path = os.path.join(
            dest_dir,
            "aces.ocio"
        )
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        shutil.copyfile(src_path, dest_path)

        yield dest_path

    @pytest.fixture(scope="module")
    def config_path_asset(
        self,
        download_test_data,
        output_folder_url
    ):
        src_path = os.path.join(
            download_test_data,
            "input",
            "data",
            "configs",
            "aces_1.3",
            "ayon_aces_config_asset.ocio"
        )
        dest_dir = os.path.join(
            output_folder_url,
            self.PROJECT,
            self.HIERARCHY,
            self.ASSET,
            "config"
        )
        dest_path = os.path.join(
            dest_dir,
            "aces.ocio"
        )
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        shutil.copyfile(src_path, dest_path)

        yield dest_path

    def test_get_colorspace_settings(self, context, config_path_asset):
        expected_config_template = (
            "{root[work]}/{project[name]}"
            "/{hierarchy}/{asset}/config/aces.ocio"
        )
        expected_file_rules = {
            "comp_review": {
                "pattern": "renderCompMain.baking_h264",
                "colorspace": "Camera Rec.709",
                "ext": "mp4"
            }
        }

        # load plugin function for testing
        plugin = publish_plugins.ColormanagedPyblishPluginMixin()
        plugin.log = log
        config_data, file_rules = plugin.get_colorspace_settings(context)

        assert config_data["template"] == expected_config_template, (
            "Returned config template is not "
            f"matching {expected_config_template}"
        )
        assert file_rules == expected_file_rules, (
            "Returned file rules are not "
            f"matching {expected_file_rules}"
        )

    def test_set_representation_colorspace(
        self, context, project_settings,
        config_path_project, config_path_asset
    ):
        expected_colorspace_hiero = "sRGB - Texture"
        expected_colorspace_nuke = "Camera Rec.709"

        config_data_nuke = colorspace.get_imageio_config(
            "test_project", "nuke", project_settings)
        file_rules_nuke = colorspace.get_imageio_file_rules(
            "test_project", "nuke", project_settings)

        config_data_hiero = colorspace.get_imageio_config(
            "test_project", "hiero", project_settings)
        file_rules_hiero = colorspace.get_imageio_file_rules(
            "test_project", "hiero", project_settings)

        representation_nuke = {
            "ext": "mp4",
            "files": "this_file_renderCompMain.baking_h264.mp4"
        }
        representation_hiero = {
            "ext": "mp4",
            "files": "this_file_renderCompMain_h264burninburnin.mp4"
        }

        # load plugin function for testing
        plugin = publish_plugins.ColormanagedPyblishPluginMixin()
        plugin.log = log
        plugin.set_representation_colorspace(
            representation_nuke, context,
            colorspace_settings=(config_data_nuke, file_rules_nuke)
        )
        # load plugin function for testing
        plugin = publish_plugins.ColormanagedPyblishPluginMixin()
        plugin.log = log
        plugin.set_representation_colorspace(
            representation_hiero, context,
            colorspace_settings=(config_data_hiero, file_rules_hiero)
        )

        colorspace_data_nuke = representation_nuke.get("colorspaceData")
        colorspace_data_hiero = representation_hiero.get("colorspaceData")

        assert colorspace_data_nuke, (
            "Colorspace data were not created in representation"
            f"matching {representation_nuke}"
        )
        assert colorspace_data_hiero, (
            "Colorspace data were not created in representation"
            f"matching {representation_hiero}"
        )

        ret_colorspace_nuke = colorspace_data_nuke["colorspace"]
        assert ret_colorspace_nuke == expected_colorspace_nuke, (
            "Returned colorspace is not "
            f"matching {expected_colorspace_nuke}"
        )
        ret_colorspace_hiero = colorspace_data_hiero["colorspace"]
        assert ret_colorspace_hiero == expected_colorspace_hiero, (
            "Returned colorspace is not "
            f"matching {expected_colorspace_hiero}"
        )


test_case = TestPipelinePublishPlugins()
