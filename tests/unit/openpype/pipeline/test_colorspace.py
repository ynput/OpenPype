

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
import logging
import shutil
import os

from tests.lib.testing_classes import ModuleUnitTest
from openpype.pipeline import colorspace, legacy_io
log = logging.getLogger("test_colorspace")


class TestPipelineColorspace(ModuleUnitTest):
    """ Testing Colorspace

    Example:
        cd to OpenPype repo root dir
        poetry run python ./start.py runtests ../tests/unit/openpype/pipeline
    """
    # PERSIST = True

    TEST_DATA_FOLDER = "C:\\CODE\\__PYPE\\__unit_testing_data\\test_pipeline_colorspace"
    TEST_FILES = [
        (
            "1JSrzYoglUzAGbJEfAOa91AeyB6fvGBOK",
            "test_pipeline_colorspace.zip",
            ""
        )
    ]

    @pytest.fixture(scope="module")
    def legacy_io(self, dbcon):
        legacy_io.install()
        yield legacy_io.Session

    @pytest.fixture(scope="module")
    def output_folder_url(self, download_test_data):
        """Returns location of published data, cleans it first if exists."""
        path = os.path.join(download_test_data, "output")
        if os.path.exists(path):
            print("Purging {}".format(path))
            shutil.rmtree(path)
        yield path

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
            "ocio"
        )
        print(f"__ dest_dir: {dest_dir}")
        dest_path = os.path.join(
            dest_dir,
            "config.ocio"
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
            "ocio"
        )
        print(f"__ dest_dir: {dest_dir}")
        dest_path = os.path.join(
            dest_dir,
            "config.ocio"
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
        expected_template = "{root[work]}/{project[name]}/ocio/config.ocio"

        # get config_data from hiero
        # where project level config is defined
        config_data = colorspace.get_imageio_config(
            "test_project", "hiero", project_settings)

        assert os.path.exists(config_data["path"]), (
            f"Config file \'{config_data['path']}\' doesn't exist"
        )
        assert config_data["template"] == expected_template, (
            f"Config template \'{config_data['template']}\' doesn't match "
            f"expected tempalte \'{expected_template}\'"
        )

    def test_parse_colorspace_from_filepath(
        self,
        legacy_io,
        config_path_asset
    ):

        config_data = {
            "path": config_path_asset
        }

        path = "renderCompMain_ACES_-_ACES2065-1.####.exr"

        expected = "ACES2065-1"

        ret = colorspace.parse_colorspace_from_filepath(
            path, "nuke", "test_project", config_data=config_data
        )

        assert ret == expected, f"Not matching colorspace {expected}"

    def test_get_ocio_config_views(self, config_path_asset):
        expected_num_keys = 12

        ret = colorspace.get_ocio_config_views(config_path_asset)

        assert len(ret) == expected_num_keys, (
            f"Not matching num viewer keys {expected_num_keys}")


test_case = TestPipelineColorspace()
