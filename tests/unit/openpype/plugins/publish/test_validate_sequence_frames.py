

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
import logging

from pyblish.api import Instance as PyblishInstance

from tests.lib.testing_classes import BaseTest
from openpype.plugins.publish.validate_sequence_frames import (
    ValidateSequenceFrames
)

log = logging.getLogger(__name__)


class TestValidateSequenceFrames(BaseTest):
    """ Testing ValidateSequenceFrames plugin

    """

    @pytest.fixture
    def instance(self):

        class Instance(PyblishInstance):
            data = {
                "frameStart": 1001,
                "frameEnd": 1002,
                "representations": []
            }
        yield Instance

    @pytest.fixture(scope="module")
    def plugin(self):
        plugin = ValidateSequenceFrames()
        plugin.log = log

        yield plugin

    def test_validate_sequence_frames_single_frame(self, instance, plugin):
        representations = [
            {
                "ext": "exr",
                "files": "Main_beauty.1001.exr",
            }
        ]
        instance.data["representations"] = representations
        instance.data["frameEnd"] = 1001

        plugin.process(instance)

    @pytest.mark.parametrize("files",
                             [
                              ["Main_beauty.v001.1001.exr",
                               "Main_beauty.v001.1002.exr"],
                              ["Main_beauty_v001.1001.exr",
                               "Main_beauty_v001.1002.exr"],
                              ["Main_beauty.1001.1001.exr",
                               "Main_beauty.1001.1002.exr"],
                              ["Main_beauty_v001_1001.exr",
                               "Main_beauty_v001_1002.exr"]])
    def test_validate_sequence_frames_name(self, instance,
                                           plugin, files):
        # tests for names with number inside, caused clique failure before
        representations = [
            {
                "ext": "exr",
                "files": files,
            }
        ]
        instance.data["representations"] = representations

        plugin.process(instance)

    @pytest.mark.parametrize("files",
                             [["Main_beauty.1001.v001.exr",
                               "Main_beauty.1002.v001.exr"]])
    def test_validate_sequence_frames_wrong_name(self, instance,
                                                 plugin, files):
        # tests for names with number inside, caused clique failure before
        representations = [
            {
                "ext": "exr",
                "files": files,
            }
        ]
        instance.data["representations"] = representations

        with pytest.raises(AssertionError) as excinfo:
            plugin.process(instance)
        assert ("Must detect single collection" in
                str(excinfo.value))

    @pytest.mark.parametrize("files",
                             [["Main_beauty.v001.1001.ass.gz",
                               "Main_beauty.v001.1002.ass.gz"]])
    def test_validate_sequence_frames_possible_wrong_name(
            self, instance, plugin, files):
        # currently pattern fails on extensions with dots
        representations = [
            {
                "files": files,
            }
        ]
        instance.data["representations"] = representations

        with pytest.raises(AssertionError) as excinfo:
            plugin.process(instance)
        assert ("Must not have remainder" in
                str(excinfo.value))

    @pytest.mark.parametrize("files",
                             [["Main_beauty.v001.1001.ass.gz",
                               "Main_beauty.v001.1002.ass.gz"]])
    def test_validate_sequence_frames__correct_ext(
            self, instance, plugin, files):
        # currently pattern fails on extensions with dots
        representations = [
            {
                "ext": "ass.gz",
                "files": files,
            }
        ]
        instance.data["representations"] = representations

        plugin.process(instance)

    def test_validate_sequence_frames_multi_frame(self, instance, plugin):
        representations = [
            {
                "ext": "exr",
                "files": ["Main_beauty.1001.exr", "Main_beauty.1002.exr",
                          "Main_beauty.1003.exr"]
            }
        ]
        instance.data["representations"] = representations
        instance.data["frameEnd"] = 1003

        plugin.process(instance)

    def test_validate_sequence_frames_multi_frame_missing(self, instance,
                                                          plugin):
        representations = [
            {
                "ext": "exr",
                "files": ["Main_beauty.1001.exr", "Main_beauty.1002.exr"]
            }
        ]
        instance.data["representations"] = representations
        instance.data["frameEnd"] = 1003

        with pytest.raises(ValueError) as excinfo:
            plugin.process(instance)
        assert ("Invalid frame range: (1001, 1002) - expected: (1001, 1003)" in
                str(excinfo.value))

    def test_validate_sequence_frames_multi_frame_hole(self, instance, plugin):
        representations = [
            {
                "ext": "exr",
                "files": ["Main_beauty.1001.exr", "Main_beauty.1003.exr"]
            }
        ]
        instance.data["representations"] = representations
        instance.data["frameEnd"] = 1003

        with pytest.raises(AssertionError) as excinfo:
            plugin.process(instance)
        assert ("Missing frames: [1002]" in str(excinfo.value))

    def test_validate_sequence_frames_slate(self, instance, plugin):
        representations = [
            {
                "ext": "exr",
                "files": [
                    "Main_beauty.1000.exr",
                    "Main_beauty.1001.exr",
                    "Main_beauty.1002.exr",
                    "Main_beauty.1003.exr"
                ]
            }
        ]
        instance.data["slate"] = True
        instance.data["representations"] = representations
        instance.data["frameEnd"] = 1003

        plugin.process(instance)


test_case = TestValidateSequenceFrames()
