

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
import os

from tests.lib.testing_classes import ModuleUnitTest
from openpype.pipeline import colorspace, legacy_io
log = logging.getLogger("test_colorspace")


class TestPipelineColorspace(ModuleUnitTest):

    TEST_DATA_FOLDER = "C:\\CODE\\__PYPE\\__unit_testing_data\\test_pipeline_colorspace"
    TEST_FILES = [
        (
            "1JSrzYoglUzAGbJEfAOa91AeyB6fvGBOK",
            "test_pipeline_colorspace.zip",
            ""
        )
    ]

    @pytest.fixture(scope="module")
    def config_path(self, download_test_data):
        yield os.path.join(
            download_test_data,
            "input",
            "data",
            "configs",
            "aces_1.2",
            "ayon_aces_config.ocio",
        )

    def test_config_file_exists(self, config_path):
        print(config_path)
        if not os.path.exists(config_path):
            raise ValueError(
                "Config file '{}' doesn't exist".format(config_path)
            )

    def test_parse_colorspace_from_filepath(self, dbcon, config_path):
        legacy_io.install()

        config_data = {
            "path": config_path
        }

        path = "renderCompMain_ACES_-_ACES2065-1.####.exr"

        expected = "ACES - ACES2065-1"

        ret = colorspace.parse_colorspace_from_filepath(
            path, "nuke", "test_project", config_data=config_data
        )

        assert ret == expected, f"Not matching colorspace {expected}"

    def test_get_ocio_config_views(self, config_path):
        expected = {
            "AYON/test_sRGB": {
                "display": "AYON", "view": "test_sRGB"},
            "ACES/sRGB": {
                "display": "ACES", "view": "sRGB"},
            "ACES/DCDM": {
                "display": "ACES", "view": "DCDM"},
            "ACES/DCDM P3D60 Limited": {
                "display": "ACES", "view": "DCDM P3D60 Limited"},
            "ACES/DCDM P3D65 Limited": {
                "display": "ACES", "view": "DCDM P3D65 Limited"},
            "ACES/P3-D60": {
                "display": "ACES", "view": "P3-D60"},
            "ACES/P3-DCI D60 simulation": {
                "display": "ACES", "view": "P3-DCI D60 simulation"},
            "ACES/P3-DCI D65 simulation": {
                "display": "ACES", "view": "P3-DCI D65 simulation"},
            "ACES/P3D65": {
                "display": "ACES", "view": "P3D65"},
            "ACES/P3D65 D60 simulation": {
                "display": "ACES", "view": "P3D65 D60 simulation"},
            "ACES/P3D65 Rec.709 Limited": {
                "display": "ACES", "view": "P3D65 Rec.709 Limited"},
            "ACES/Rec.2020": {
                "display": "ACES", "view": "Rec.2020"},
            "ACES/Rec.2020 P3D65 Limited": {
                "display": "ACES", "view": "Rec.2020 P3D65 Limited"},
            "ACES/Rec.2020 Rec.709 Limited": {
                "display": "ACES", "view": "Rec.2020 Rec.709 Limited"},
            "ACES/Rec.2020 HLG 1000 nits": {
                "display": "ACES", "view": "Rec.2020 HLG 1000 nits"},
            "ACES/Rec.709": {
                "display": "ACES", "view": "Rec.709"},
            "ACES/Rec.709 D60 sim.": {
                "display": "ACES", "view": "Rec.709 D60 sim."},
            "ACES/sRGB D60 sim.": {
                "display": "ACES", "view": "sRGB D60 sim."},
            "ACES/Raw": {
                "display": "ACES", "view": "Raw"},
            "ACES/Log": {
                "display": "ACES", "view": "Log"}
        }

        ret = colorspace.get_ocio_config_views(config_path)

        assert ret == expected, f"Not matching colorspace {expected}"


test_case = TestPipelineColorspace()
