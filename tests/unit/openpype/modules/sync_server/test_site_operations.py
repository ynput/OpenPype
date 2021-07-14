"""Test file for Sync Server, tests site operations add_site, remove_site.

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

from tests.lib.testing_wrapper import TestCase
from bson.objectid import ObjectId


class TestSiteOperation(TestCase):

    @pytest.fixture(scope="module")
    def setup_sync_server_module(self, db):
        """Get sync_server_module from ModulesManager"""
        from openpype.modules import ModulesManager
    
        manager = ModulesManager()
        sync_server = manager.modules_by_name["sync_server"]
        yield sync_server
    
    
    @pytest.mark.usefixtures("db")
    def test_project_created(self, db):
        assert ['test_project'] == db.database.collection_names(False)
    
    
    @pytest.mark.usefixtures("db")
    def test_objects_imported(self, db):
        count_obj = len(list(db.database[self.TEST_PROJECT_NAME].find({})))
        assert 15 == count_obj
    
    
    @pytest.mark.usefixtures("setup_sync_server_module")
    def test_add_site(self, db, setup_sync_server_module):
        """Adds 'test_site', checks that added, checks that doesn't duplicate."""
        query = {
            "_id": ObjectId(self.REPRESENTATION_ID)
        }
    
        ret = db.database[self.TEST_PROJECT_NAME].find(query)
    
        assert 1 == len(list(ret)), \
            "Single {} must be in DB".format(self.REPRESENTATION_ID)
    
        setup_sync_server_module.add_site(self.TEST_PROJECT_NAME, self.REPRESENTATION_ID,
                                          site_name='test_site')
    
        ret = list(db.database[self.TEST_PROJECT_NAME].find(query))
    
        assert 1 == len(ret), \
            "Single {} must be in DB".format(self.REPRESENTATION_ID)
    
        ret = ret.pop()
        site_names = [site["name"] for site in ret["files"][0]["sites"]]
        assert 'test_site' in site_names, "Site name wasn't added"
    
    
    @pytest.mark.usefixtures("setup_sync_server_module")
    def test_add_site_again(self, db, setup_sync_server_module):
        """Depends on test_add_site, must throw exception."""
        with pytest.raises(ValueError):
            setup_sync_server_module.add_site(self.TEST_PROJECT_NAME, self.REPRESENTATION_ID,
                                              site_name='test_site')
    
    
    @pytest.mark.usefixtures("setup_sync_server_module")
    def test_add_site_again_force(self, db, setup_sync_server_module):
        """Depends on test_add_site, must not throw exception."""
        setup_sync_server_module.add_site(self.TEST_PROJECT_NAME, self.REPRESENTATION_ID,
                                          site_name='test_site', force=True)
    
        query = {
            "_id": ObjectId(self.REPRESENTATION_ID)
        }
    
        ret = list(db.database[self.TEST_PROJECT_NAME].find(query))
    
        assert 1 == len(ret), \
            "Single {} must be in DB".format(self.REPRESENTATION_ID)
    
    
    @pytest.mark.usefixtures("setup_sync_server_module")
    def test_remove_site(self, db, setup_sync_server_module):
        """Depends on test_add_site, must remove 'test_site'."""
        setup_sync_server_module.remove_site(self.TEST_PROJECT_NAME, self.REPRESENTATION_ID,
                                             site_name='test_site')
    
        query = {
            "_id": ObjectId(self.REPRESENTATION_ID)
        }
    
        ret = list(db.database[self.TEST_PROJECT_NAME].find(query))
    
        assert 1 == len(ret), \
            "Single {} must be in DB".format(self.REPRESENTATION_ID)
    
        ret = ret.pop()
        site_names = [site["name"] for site in ret["files"][0]["sites"]]
    
        assert 'test_site' not in site_names, "Site name wasn't removed"
    
    
    @pytest.mark.usefixtures("setup_sync_server_module")
    def test_remove_site_again(self, db, setup_sync_server_module):
        """Depends on test_add_site, must trow exception"""
        with pytest.raises(ValueError):
            setup_sync_server_module.remove_site(self.TEST_PROJECT_NAME,
                                                 self.REPRESENTATION_ID,
                                                 site_name='test_site')
    
        query = {
            "_id": ObjectId(self.REPRESENTATION_ID)
        }
    
        ret = list(db.database[self.TEST_PROJECT_NAME].find(query))
    
        assert 1 == len(ret), \
            "Single {} must be in DB".format(self.REPRESENTATION_ID)


test_case = TestSiteOperation()