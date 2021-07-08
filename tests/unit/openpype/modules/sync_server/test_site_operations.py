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
import os
import pytest
import tempfile
import shutil
from bson.objectid import ObjectId

from tests.lib.db_handler import DBHandler
from tests.lib.file_handler import RemoteFileHandler

TEST_DB_NAME = "test_db"
TEST_PROJECT_NAME = "test_project"
TEST_OPENPYPE_NAME = "test_openpype"
REPRESENTATION_ID = "60e578d0c987036c6a7b741d"

TEST_FILES = [
    ("1eCwPljuJeOI8A3aisfOIBKKjcmIycTEt", "test_site_operations.zip", "")
]


@pytest.fixture(scope='session')
def monkeypatch_session():
    """Monkeypatch couldn't be used with module or session fixtures."""
    from _pytest.monkeypatch import MonkeyPatch
    m = MonkeyPatch()
    yield m
    m.undo()


@pytest.fixture(scope="module")
def download_test_data():
    tmpdir = tempfile.mkdtemp()
    for test_file in TEST_FILES:
        file_id, file_name, md5 = test_file

        f_name, ext = os.path.splitext(file_name)

        RemoteFileHandler.download_file_from_google_drive(file_id,
                                                          str(tmpdir),
                                                          file_name)

        if ext.lstrip('.') in RemoteFileHandler.IMPLEMENTED_ZIP_FORMATS:
            RemoteFileHandler.unzip(os.path.join(tmpdir, file_name))


        yield tmpdir
        shutil.rmtree(tmpdir)


@pytest.fixture(scope="module")
def db(monkeypatch_session, download_test_data):
    backup_dir = download_test_data

    uri = os.environ.get("OPENPYPE_MONGO") or "mongodb://localhost:27017"
    db_handler = DBHandler(uri)
    db_handler.setup_from_dump(TEST_DB_NAME, backup_dir, True,
                               db_name_out=TEST_DB_NAME)

    db_handler.setup_from_dump("openpype", backup_dir, True,
                               db_name_out=TEST_OPENPYPE_NAME)

    # set needed env vars temporarily for tests
    monkeypatch_session.setenv("OPENPYPE_MONGO", uri)
    monkeypatch_session.setenv("AVALON_MONGO", uri)
    monkeypatch_session.setenv("OPENPYPE_DATABASE_NAME", TEST_OPENPYPE_NAME)
    monkeypatch_session.setenv("AVALON_TIMEOUT", '3000')
    monkeypatch_session.setenv("AVALON_DB", TEST_DB_NAME)
    monkeypatch_session.setenv("AVALON_PROJECT", TEST_PROJECT_NAME)
    monkeypatch_session.setenv("PYPE_DEBUG", "3")

    from avalon.api import AvalonMongoDB
    db = AvalonMongoDB()
    yield db

    db_handler.teardown(TEST_DB_NAME)
    db_handler.teardown(TEST_OPENPYPE_NAME)

@pytest.fixture(scope="module")
def setup_sync_server_module(db):
    """Get sync_server_module from ModulesManager"""
    from openpype.modules import ModulesManager

    manager = ModulesManager()
    sync_server = manager.modules_by_name["sync_server"]
    yield sync_server


@pytest.mark.usefixtures("db")
def test_project_created(db):
    assert ['test_project'] == db.database.collection_names(False)


@pytest.mark.usefixtures("db")
def test_objects_imported(db):
    count_obj = len(list(db.database[TEST_PROJECT_NAME].find({})))
    assert 15 == count_obj


@pytest.mark.usefixtures("setup_sync_server_module")
def test_add_site(db, setup_sync_server_module):
    """Adds 'test_site', checks that added, checks that doesn't duplicate."""
    query = {
        "_id": ObjectId(REPRESENTATION_ID)
    }

    ret = db.database[TEST_PROJECT_NAME].find(query)

    assert 1 == len(list(ret)), \
        "Single {} must be in DB".format(REPRESENTATION_ID)

    setup_sync_server_module.add_site(TEST_PROJECT_NAME, REPRESENTATION_ID,
                                      site_name='test_site')

    ret = list(db.database[TEST_PROJECT_NAME].find(query))

    assert 1 == len(ret), \
        "Single {} must be in DB".format(REPRESENTATION_ID)

    ret = ret.pop()
    site_names = [site["name"] for site in ret["files"][0]["sites"]]
    assert 'test_site' in site_names, "Site name wasn't added"


@pytest.mark.usefixtures("setup_sync_server_module")
def test_add_site_again(db, setup_sync_server_module):
    """Depends on test_add_site, must throw exception."""
    with pytest.raises(ValueError):
        setup_sync_server_module.add_site(TEST_PROJECT_NAME, REPRESENTATION_ID,
                                          site_name='test_site')


@pytest.mark.usefixtures("setup_sync_server_module")
def test_add_site_again_force(db, setup_sync_server_module):
    """Depends on test_add_site, must not throw exception."""
    setup_sync_server_module.add_site(TEST_PROJECT_NAME, REPRESENTATION_ID,
                                      site_name='test_site', force=True)

    query = {
        "_id": ObjectId(REPRESENTATION_ID)
    }

    ret = list(db.database[TEST_PROJECT_NAME].find(query))

    assert 1 == len(ret), \
        "Single {} must be in DB".format(REPRESENTATION_ID)


@pytest.mark.usefixtures("setup_sync_server_module")
def test_remove_site(db, setup_sync_server_module):
    """Depends on test_add_site, must remove 'test_site'."""
    setup_sync_server_module.remove_site(TEST_PROJECT_NAME, REPRESENTATION_ID,
                                         site_name='test_site')

    query = {
        "_id": ObjectId(REPRESENTATION_ID)
    }

    ret = list(db.database[TEST_PROJECT_NAME].find(query))

    assert 1 == len(ret), \
        "Single {} must be in DB".format(REPRESENTATION_ID)

    ret = ret.pop()
    site_names = [site["name"] for site in ret["files"][0]["sites"]]

    assert 'test_site' not in site_names, "Site name wasn't removed"


@pytest.mark.usefixtures("setup_sync_server_module")
def test_remove_site_again(db, setup_sync_server_module):
    """Depends on test_add_site, must trow exception"""
    with pytest.raises(ValueError):
        setup_sync_server_module.remove_site(TEST_PROJECT_NAME,
                                             REPRESENTATION_ID,
                                             site_name='test_site')

    query = {
        "_id": ObjectId(REPRESENTATION_ID)
    }

    ret = list(db.database[TEST_PROJECT_NAME].find(query))

    assert 1 == len(ret), \
        "Single {} must be in DB".format(REPRESENTATION_ID)
