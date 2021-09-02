import os
import sys
import six
import json
import pytest
import tempfile
import shutil

from tests.lib.db_handler import DBHandler
from tests.lib.file_handler import RemoteFileHandler


class TestCase:
    """Generic test class for testing

        Implemented fixtures:
            monkeypatch_session - fixture for env vars with session scope
            download_test_data - tmp folder with extracted data from GDrive
            env_var - sets env vars from input file
            db_setup - prepares avalon AND openpype DBs for testing from
                        binary dumps from input data
            dbcon - returns DBConnection to AvalonDB
            dbcon_openpype - returns DBConnection for OpenpypeMongoDB

        Not implemented:
            last_workfile_path - returns path to testing workfile

    """
    TEST_OPENPYPE_MONGO = "mongodb://localhost:27017"
    TEST_DB_NAME = "test_db"
    TEST_PROJECT_NAME = "test_project"
    TEST_OPENPYPE_NAME = "test_openpype"

    REPRESENTATION_ID = "60e578d0c987036c6a7b741d"

    TEST_FILES = []

    PROJECT = "test_project"
    ASSET = "test_asset"
    TASK = "test_task"

    @pytest.fixture(scope='session')
    def monkeypatch_session(self):
        """Monkeypatch couldn't be used with module or session fixtures."""
        from _pytest.monkeypatch import MonkeyPatch
        m = MonkeyPatch()
        yield m
        m.undo()

    @pytest.fixture(scope="module")
    def download_test_data(self):
        tmpdir = tempfile.mkdtemp()
        for test_file in self.TEST_FILES:
            file_id, file_name, md5 = test_file

            f_name, ext = os.path.splitext(file_name)

            RemoteFileHandler.download_file_from_google_drive(file_id,
                                                              str(tmpdir),
                                                              file_name)

            if ext.lstrip('.') in RemoteFileHandler.IMPLEMENTED_ZIP_FORMATS:
                RemoteFileHandler.unzip(os.path.join(tmpdir, file_name))

            yield tmpdir
            print("Removing {}".format(tmpdir))
            shutil.rmtree(tmpdir)

    @pytest.fixture(scope="module")
    def env_var(self, monkeypatch_session, download_test_data):
        """Sets temporary env vars from json file."""
        env_url = os.path.join(download_test_data, "input",
                               "env_vars", "env_var.json")
        if not os.path.exists(env_url):
            raise ValueError("Env variable file {} doesn't exist".
                             format(env_url))

        env_dict = {}
        try:
            with open(env_url) as json_file:
                env_dict = json.load(json_file)
        except ValueError:
            print("{} doesn't contain valid JSON")
            six.reraise(*sys.exc_info())

        for key, value in env_dict.items():
            all_vars = globals()
            all_vars.update(vars(TestCase))  # TODO check
            value = value.format(**all_vars)
            print("Setting {}:{}".format(key, value))
            monkeypatch_session.setenv(key, value)
        import openpype

        openpype_root = os.path.dirname(os.path.dirname(openpype.__file__))
        # ?? why 2 of those
        monkeypatch_session.setenv("OPENPYPE_ROOT", openpype_root)
        monkeypatch_session.setenv("OPENPYPE_REPOS_ROOT", openpype_root)

    @pytest.fixture(scope="module")
    def db_setup(self, download_test_data, env_var, monkeypatch_session):
        """Restore prepared MongoDB dumps into selected DB."""
        backup_dir = os.path.join(download_test_data, "input", "dumps")

        uri = os.environ.get("OPENPYPE_MONGO")
        db_handler = DBHandler(uri)
        db_handler.setup_from_dump(self.TEST_DB_NAME, backup_dir, True,
                                   db_name_out=self.TEST_DB_NAME)

        db_handler.setup_from_dump("openpype", backup_dir, True,
                                   db_name_out=self.TEST_OPENPYPE_NAME)

        yield db_handler

        db_handler.teardown(self.TEST_DB_NAME)
        db_handler.teardown(self.TEST_OPENPYPE_NAME)

    @pytest.fixture(scope="module")
    def dbcon(self, db_setup):
        """Provide test database connection.

            Database prepared from dumps with 'db_setup' fixture.
        """
        from avalon.api import AvalonMongoDB
        dbcon = AvalonMongoDB()
        dbcon.Session["AVALON_PROJECT"] = self.TEST_PROJECT_NAME
        yield dbcon

    @pytest.fixture(scope="module")
    def dbcon_openpype(self, db_setup):
        """Provide test database connection for OP settings.

            Database prepared from dumps with 'db_setup' fixture.
        """
        from openpype.lib import OpenPypeMongoConnection
        mongo_client = OpenPypeMongoConnection.get_mongo_client()
        yield mongo_client[self.TEST_OPENPYPE_NAME]["settings"]

    @pytest.fixture(scope="module")
    def last_workfile_path(self, download_test_data):
        raise NotImplemented

    @pytest.fixture(scope="module")
    def startup_scripts(self, monkeypatch_session, download_test_data):
        raise NotImplemented
