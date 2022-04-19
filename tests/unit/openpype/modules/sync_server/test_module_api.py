"""Test file for Sync Server, tests API methods, currently for integrate_new

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

from tests.lib.testing_classes import ModuleUnitTest


class TestModuleApi(ModuleUnitTest):

    REPRESENTATION_ID = "60e578d0c987036c6a7b741d"

    TEST_FILES = [("1eCwPljuJeOI8A3aisfOIBKKjcmIycTEt",
                   "test_site_operations.zip", '')]

    @pytest.fixture(scope="module")
    def setup_sync_server_module(self, dbcon):
        """Get sync_server_module from ModulesManager"""
        from openpype.modules import ModulesManager

        manager = ModulesManager()
        sync_server = manager.modules_by_name["sync_server"]
        yield sync_server

    def test_get_alt_site_pairs(self, setup_sync_server_module):
        conf_sites = {"SFTP": {"alternative_sites": ["studio"]},
                      "studio2": {"alternative_sites": ["studio"]}}

        ret = setup_sync_server_module._get_alt_site_pairs(conf_sites)
        expected = {"SFTP": {"studio", "studio2"},
                    "studio": {"SFTP", "studio2"},
                    "studio2": {"studio", "SFTP"}}
        assert ret == expected, "Not matching result"


test_case = TestModuleApi()
