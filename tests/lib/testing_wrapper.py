import os
import sys
import six
import json
import pytest
import tempfile
import shutil
from bson.objectid import ObjectId

from tests.lib.db_handler import DBHandler
from tests.lib.file_handler import RemoteFileHandler


class TestCase():

    TEST_OPENPYPE_MONGO = "mongodb://localhost:27017"
    TEST_DB_NAME = "test_db"
    TEST_PROJECT_NAME = "test_project"
    TEST_OPENPYPE_NAME = "test_openpype"

    REPRESENTATION_ID = "60e578d0c987036c6a7b741d"

    TEST_FILES = [
        ("1eCwPljuJeOI8A3aisfOIBKKjcmIycTEt", "test_site_operations.zip", "")
    ]

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
            shutil.rmtree(tmpdir)


    @pytest.fixture(scope="module")
    def env_var(self, monkeypatch_session, download_test_data):
        """Sets temporary env vars from json file."""
        env_url = os.path.join(download_test_data, "input",
                               "env_vars", "env_var.json")
        if not os.path.exists(env_url):
            raise ValueError("Env variable file {} doesn't exist".format(env_url))

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

    @pytest.fixture(scope="module")
    def db_setup(self, download_test_data, env_var, monkeypatch_session):
        """Restore prepared MongoDB dumps into selected DB."""
        backup_dir = os.path.join(download_test_data, "input", "dumps")

        uri = os.environ.get("OPENPYPE_MONGO") or "mongodb://localhost:27017"
        db_handler = DBHandler(uri)
        db_handler.setup_from_dump(self.TEST_DB_NAME, backup_dir, True,
                                   db_name_out=self.TEST_DB_NAME)

        db_handler.setup_from_dump("openpype", backup_dir, True,
                                   db_name_out=self.TEST_OPENPYPE_NAME)

        yield db_handler

        db_handler.teardown(self.TEST_DB_NAME)
        db_handler.teardown(self.TEST_OPENPYPE_NAME)


    @pytest.fixture(scope="module")
    def db(self, db_setup):
        """Provide test database connection.

            Database prepared from dumps with 'db_setup' fixture.
        """
        from avalon.api import AvalonMongoDB
        db = AvalonMongoDB()
        yield db
