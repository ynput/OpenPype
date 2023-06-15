

"""Test Colorspace pipeline modul, tests API methods

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
import pytest
import shutil
import os

from tests.unit.openpype.pipeline.lib import TestPipeline
from openpype.pipeline import colorspace


class TestPipelineColorspace(TestPipeline):
    """ Testing Colorspace

    Example:
        cd to OpenPype repo root dir
        poetry run python ./start.py runtests ../tests/unit/openpype/pipeline
    """

    TEST_FILES = [
        (
            "1Lf-mFxev7xiwZCWfImlRcw7Fj8XgNQMh",
            "test_pipeline_colorspace.zip",
            ""
        )
    ]

    PROJECT = "test_project"
    ASSET = "test_asset"
    TASK = "test_task"

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

    def test_config_file_project(
        self,
        legacy_io,
        config_path_project,
        project_settings
    ):
        expected_template = "{root[work]}/{project[name]}/config/aces.ocio"

        # get config_data from hiero
        # where project level config is defined
        config_data = colorspace.get_imageio_config(
            "test_project", "hiero", project_settings)

        assert os.path.exists(config_data["path"]), (
            f"Config file \'{config_data['path']}\' doesn't exist"
        )
        assert config_data["template"] == expected_template, (
            f"Config template \'{config_data['template']}\' doesn't match "
            f"expected template \'{expected_template}\'"
        )

    def test_parse_colorspace_from_filepath(
        self,
        legacy_io,
        config_path_asset,
        project_settings
    ):
        path_1 = "renderCompMain_ACES2065-1.####.exr"
        expected_1 = "ACES2065-1"
        ret_1 = colorspace.parse_colorspace_from_filepath(
            path_1, "nuke", "test_project", project_settings=project_settings
        )
        assert ret_1 == expected_1, f"Not matching colorspace {expected_1}"

        path_2 = "renderCompMain_BMDFilm_WideGamut_Gen5.mov"
        expected_2 = "BMDFilm WideGamut Gen5"
        ret_2 = colorspace.parse_colorspace_from_filepath(
            path_2, "nuke", "test_project", project_settings=project_settings
        )
        assert ret_2 == expected_2, f"Not matching colorspace {expected_2}"

    def test_get_ocio_config_views_asset(self, config_path_asset):
        expected_num_keys = 12

        ret = colorspace.get_ocio_config_views(config_path_asset)

        assert len(ret) == expected_num_keys, (
            f"Not matching num viewer keys {expected_num_keys}")

    def test_get_ocio_config_views_project(self, config_path_project):
        expected_num_keys = 3

        ret = colorspace.get_ocio_config_views(config_path_project)

        assert len(ret) == expected_num_keys, (
            f"Not matching num viewer keys {expected_num_keys}")

    def test_file_rules(self, project_settings):
        expected_nuke = {
            "comp_review": {
                "pattern": "renderCompMain.baking_h264",
                "colorspace": "Camera Rec.709",
                "ext": "mp4"
            }
        }
        expected_hiero = {
            "comp_review": {
                "pattern": "renderCompMain_h264burninburnin",
                "colorspace": "sRGB - Texture",
                "ext": "mp4"
            }
        }

        nuke_file_rules = colorspace.get_imageio_file_rules(
            "test_project", "nuke", project_settings=project_settings)
        assert expected_nuke == nuke_file_rules, (
            f"Not matching file rules {expected_nuke}")

        hiero_file_rules = colorspace.get_imageio_file_rules(
            "test_project", "hiero", project_settings=project_settings)
        assert expected_hiero == hiero_file_rules, (
            f"Not matching file rules {expected_hiero}")


test_case = TestPipelineColorspace()
