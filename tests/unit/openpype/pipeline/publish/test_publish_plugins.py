

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
import pytest
import os

from tests.unit.openpype.pipeline.lib import TestPipeline
from openpype.pipeline.publish import publish_plugins


class TestPipelinePublishPlugins(TestPipeline):
    """ Testing Pipeline pubish_plugins.py

    Example:
        cd to OpenPype repo root dir
        poetry run python ./start.py runtests \
            ../tests/unit/openpype/pipeline/publish
    """

    # files are the same as those used in `test_pipeline_colorspace`
    TEST_FILES = [
        (
            "1uhWvVdJBUSetpPVG8OzSjYXH4voIpf_G",
            "test_pipeline_colorspace.zip",
            ""
        )
    ]

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

    def test_config_file_project(self, context):
        expected_config_template = (
            "{root[work]}/{project[name]}/{asset}/ocio/config.ocio")
        expected_file_rules = {
            "comp_review": {
                "pattern": "renderCompMain.baking_h264",
                "colorspace": "Output - Rec.709",
                "ext": "mp4"
            }
        }
        plugin = publish_plugins.ExtractorColormanaged()
        config_data, file_rules = plugin.get_colorspace_settings(context)

        assert config_data["template"] == expected_config_template, (
            "Returned config tempate is not "
            f"matching {expected_config_template}"
        )
        assert file_rules == expected_file_rules, (
            "Returned file rules are not "
            f"matching {expected_file_rules}"
        )


test_case = TestPipelinePublishPlugins()
