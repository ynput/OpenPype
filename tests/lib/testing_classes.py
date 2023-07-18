"""Testing classes for module testing and publishing in hosts."""
import os
import sys
import six
import json
import pytest
import tempfile
import shutil
import glob
import platform
import requests
import re

from tests.lib.db_handler import DBHandler
from common.ayon_common.distribution.file_handler import RemoteFileHandler
from openpype.modules import ModulesManager
from openpype.settings import get_project_settings


class BaseTest:
    """Empty base test class"""


class ModuleUnitTest(BaseTest):
    """Generic test class for testing modules

        Use PERSIST==True to keep temporary folder and DB prepared for
        debugging or preparation of test files.

        Implemented fixtures:
            monkeypatch_session - fixture for env vars with session scope
            project_settings - fixture for project settings with session scope
            download_test_data - tmp folder with extracted data from GDrive
            env_var - sets env vars from input file
            db_setup - prepares avalon AND openpype DBs for testing from
                        binary dumps from input data
            dbcon - returns DBConnection to AvalonDB
            dbcon_openpype - returns DBConnection for OpenpypeMongoDB

    """
    PERSIST = False  # True to not purge temporary folder nor test DB

    TEST_OPENPYPE_MONGO = "mongodb://localhost:27017"
    TEST_DB_NAME = "avalon_tests"
    TEST_PROJECT_NAME = "test_project"
    TEST_OPENPYPE_NAME = "openpype_tests"

    TEST_FILES = []

    PROJECT = "test_project"
    ASSET = "test_asset"
    TASK = "test_task"

    TEST_DATA_FOLDER = None

    @pytest.fixture(scope='session')
    def monkeypatch_session(self):
        """Monkeypatch couldn't be used with module or session fixtures."""
        from _pytest.monkeypatch import MonkeyPatch
        m = MonkeyPatch()
        yield m
        m.undo()

    @pytest.fixture(scope='module')
    def project_settings(self):
        yield get_project_settings(
            self.PROJECT
        )

    @pytest.fixture(scope="module")
    def download_test_data(self, test_data_folder, persist, request):
        test_data_folder = test_data_folder or self.TEST_DATA_FOLDER
        if test_data_folder:
            print("Using existing folder {}".format(test_data_folder))
            yield test_data_folder
        else:
            tmpdir = tempfile.mkdtemp()
            print("Temporary folder created:: {}".format(tmpdir))
            for test_file in self.TEST_FILES:
                file_id, file_name, md5 = test_file

                f_name, ext = os.path.splitext(file_name)

                RemoteFileHandler.download_file_from_google_drive(file_id,
                                                                  str(tmpdir),
                                                                  file_name)

                if ext.lstrip('.') in RemoteFileHandler.IMPLEMENTED_ZIP_FORMATS:  # noqa: E501
                    RemoteFileHandler.unzip(os.path.join(tmpdir, file_name))
                yield tmpdir

                persist = (persist or self.PERSIST or
                           self.is_test_failed(request))
                if not persist:
                    print("Removing {}".format(tmpdir))
                    shutil.rmtree(tmpdir)

    @pytest.fixture(scope="module")
    def output_folder_url(self, download_test_data):
        """Returns location of published data, cleans it first if exists."""
        path = os.path.join(download_test_data, "output")
        if os.path.exists(path):
            print("Purging {}".format(path))
            shutil.rmtree(path)
        yield path

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
            all_vars.update(vars(ModuleUnitTest))  # TODO check
            value = value.format(**all_vars)
            print("Setting {}:{}".format(key, value))
            monkeypatch_session.setenv(key, str(value))

        #reset connection to openpype DB with new env var
        import openpype.settings.lib as sett_lib
        sett_lib._SETTINGS_HANDLER = None
        sett_lib._LOCAL_SETTINGS_HANDLER = None
        sett_lib.create_settings_handler()
        sett_lib.create_local_settings_handler()

        import openpype
        openpype_root = os.path.dirname(os.path.dirname(openpype.__file__))

        # ?? why 2 of those
        monkeypatch_session.setenv("OPENPYPE_ROOT", openpype_root)
        monkeypatch_session.setenv("OPENPYPE_REPOS_ROOT", openpype_root)

        # for remapping purposes (currently in Nuke)
        monkeypatch_session.setenv("TEST_SOURCE_FOLDER", download_test_data)

    @pytest.fixture(scope="module")
    def db_setup(self, download_test_data, env_var, monkeypatch_session,
                 request):
        """Restore prepared MongoDB dumps into selected DB."""
        backup_dir = os.path.join(download_test_data, "input", "dumps")

        uri = os.environ.get("OPENPYPE_MONGO")
        db_handler = DBHandler(uri)
        db_handler.setup_from_dump(self.TEST_DB_NAME, backup_dir,
                                   overwrite=True,
                                   db_name_out=self.TEST_DB_NAME)

        db_handler.setup_from_dump(self.TEST_OPENPYPE_NAME, backup_dir,
                                   overwrite=True,
                                   db_name_out=self.TEST_OPENPYPE_NAME)

        yield db_handler

        persist = self.PERSIST or self.is_test_failed(request)
        if not persist:
            db_handler.teardown(self.TEST_DB_NAME)
            db_handler.teardown(self.TEST_OPENPYPE_NAME)

    @pytest.fixture(scope="module")
    def dbcon(self, db_setup, output_folder_url):
        """Provide test database connection.

            Database prepared from dumps with 'db_setup' fixture.
        """
        from openpype.pipeline import AvalonMongoDB
        dbcon = AvalonMongoDB()
        dbcon.Session["AVALON_PROJECT"] = self.PROJECT
        dbcon.Session["AVALON_ASSET"] = self.ASSET
        dbcon.Session["AVALON_TASK"] = self.TASK

        # set project root to temp folder
        platform_str = platform.system().lower()
        root_key = "config.roots.work.{}".format(platform_str)
        dbcon.update_one(
            {"type": "project"},
            {"$set":
                {
                    root_key: output_folder_url
                }}
        )
        yield dbcon

    @pytest.fixture(scope="module")
    def dbcon_openpype(self, db_setup):
        """Provide test database connection for OP settings.

            Database prepared from dumps with 'db_setup' fixture.
        """
        from openpype.lib import OpenPypeMongoConnection
        mongo_client = OpenPypeMongoConnection.get_mongo_client()
        yield mongo_client[self.TEST_OPENPYPE_NAME]["settings"]

    def is_test_failed(self, request):
        # if request.node doesn't have rep_call, something failed
        try:
            return request.node.rep_call.failed
        except AttributeError:
            return True


class PublishTest(ModuleUnitTest):
    """Test class for publishing in hosts.

        Implemented fixtures:
            launched_app - launches APP with last_workfile_path
            publish_finished - waits until publish is finished, host must
                kill its process when finished publishing. Includes timeout
                which raises ValueError

        Not implemented:
            last_workfile_path - returns path to testing workfile
            startup_scripts - provide script for setup in host

        Implemented tests:
            test_folder_structure_same - compares published and expected
                subfolders if they contain same files. Compares only on file
                presence

            TODO: implement test on file size, file content
    """

    APP_GROUP = ""

    TIMEOUT = 120  # publish timeout

    # could be overwritten by command line arguments
    # command line value takes precedence

    # keep empty to locate latest installed variant or explicit
    APP_VARIANT = ""
    PERSIST = True  # True - keep test_db, test_openpype, outputted test files
    TEST_DATA_FOLDER = None  # use specific folder of unzipped test file

    SETUP_ONLY = False

    @pytest.fixture(scope="module")
    def app_name(self, app_variant):
        """Returns calculated value for ApplicationManager. Eg.(nuke/12-2)"""
        from openpype.lib import ApplicationManager
        app_variant = app_variant or self.APP_VARIANT

        application_manager = ApplicationManager()
        if not app_variant:
            variant = (
                application_manager.find_latest_available_variant_for_group(
                    self.APP_GROUP))
            app_variant = variant.name

        yield "{}/{}".format(self.APP_GROUP, app_variant)

    @pytest.fixture(scope="module")
    def app_args(self, download_test_data):
        """Returns additional application arguments from a test file.

            Test zip file should contain file at:
                FOLDER_DIR/input/app_args/app_args.json
            containing a list of command line arguments (like '-x' etc.)
        """
        app_args = []
        args_url = os.path.join(download_test_data, "input",
                                "app_args", "app_args.json")
        if not os.path.exists(args_url):
            print("App argument file {} doesn't exist".format(args_url))
        else:
            try:
                with open(args_url) as json_file:
                    app_args = json.load(json_file)

                if not isinstance(app_args, list):
                    raise ValueError
            except ValueError:
                print("{} doesn't contain valid JSON".format(args_url))
                six.reraise(*sys.exc_info())

        yield app_args

    @pytest.fixture(scope="module")
    def launched_app(self, dbcon, download_test_data, last_workfile_path,
                     startup_scripts, app_args, app_name, output_folder_url,
                     setup_only):
        """Launch host app"""
        if setup_only or self.SETUP_ONLY:
            print("Creating only setup for test, not launching app")
            yield
            return
        # set schema - for integrate_new
        from openpype import PACKAGE_DIR
        # Path to OpenPype's schema
        schema_path = os.path.join(
            os.path.dirname(PACKAGE_DIR),
            "schema"
        )
        os.environ["AVALON_SCHEMA"] = schema_path

        os.environ["OPENPYPE_EXECUTABLE"] = sys.executable
        from openpype.lib import ApplicationManager

        application_manager = ApplicationManager()
        data = {
            "last_workfile_path": last_workfile_path,
            "start_last_workfile": True,
            "project_name": self.PROJECT,
            "asset_name": self.ASSET,
            "task_name": self.TASK
        }
        if app_args:
            data["app_args"] = app_args

        app_process = application_manager.launch(app_name, **data)
        yield app_process

    @pytest.fixture(scope="module")
    def publish_finished(self, dbcon, launched_app, download_test_data,
                         timeout, setup_only):
        """Dummy fixture waiting for publish to finish"""
        if setup_only or self.SETUP_ONLY:
            print("Creating only setup for test, not launching app")
            yield False
            return
        import time
        time_start = time.time()
        timeout = timeout or self.TIMEOUT
        timeout = float(timeout)
        while launched_app.poll() is None:
            time.sleep(0.5)
            if time.time() - time_start > timeout:
                launched_app.terminate()
                raise ValueError("Timeout reached")

        # some clean exit test possible?
        print("Publish finished")
        yield True

    def test_folder_structure_same(self, dbcon, publish_finished,
                                   download_test_data, output_folder_url,
                                   skip_compare_folders,
                                   setup_only):
        """Check if expected and published subfolders contain same files.

            Compares only presence, not size nor content!
        """
        if setup_only or self.SETUP_ONLY:
            print("Creating only setup for test, not launching app")
            return

        published_dir_base = output_folder_url
        expected_dir_base = os.path.join(download_test_data,
                                         "expected")

        print("Comparing published:'{}' : expected:'{}'".format(
            published_dir_base, expected_dir_base))
        published = set(f.replace(published_dir_base, '') for f in
                        glob.glob(published_dir_base + "\\**", recursive=True)
                        if f != published_dir_base and os.path.exists(f))
        expected = set(f.replace(expected_dir_base, '') for f in
                       glob.glob(expected_dir_base + "\\**", recursive=True)
                       if f != expected_dir_base and os.path.exists(f))

        filtered_published = self._filter_files(published,
                                                skip_compare_folders)

        # filter out temp files also in expected
        # could be polluted by accident by copying 'output' to zip file
        filtered_expected = self._filter_files(expected, skip_compare_folders)

        not_mtched = filtered_expected.symmetric_difference(filtered_published)
        if not_mtched:
            raise AssertionError("Missing {} files".format(
                "\n".join(sorted(not_mtched))))

    def _filter_files(self, source_files, skip_compare_folders):
        """Filter list of files according to regex pattern."""
        filtered = set()
        for file_path in source_files:
            if skip_compare_folders:
                if not any([re.search(val, file_path)
                            for val in skip_compare_folders]):
                    filtered.add(file_path)
            else:
                filtered.add(file_path)

        return filtered


class DeadlinePublishTest(PublishTest):
    @pytest.fixture(scope="module")
    def publish_finished(self, dbcon, launched_app, download_test_data,
                         timeout):
        """Dummy fixture waiting for publish to finish"""
        import time
        time_start = time.time()
        timeout = timeout or self.TIMEOUT
        timeout = float(timeout)
        while launched_app.poll() is None:
            time.sleep(0.5)
            if time.time() - time_start > timeout:
                launched_app.terminate()
                raise ValueError("Timeout reached")

        metadata_json = glob.glob(os.path.join(download_test_data,
                                               "output",
                                               "**/*_metadata.json"),
                                  recursive=True)
        if not metadata_json:
            raise RuntimeError("No metadata file found. No job id.")

        if len(metadata_json) > 1:
            # depends on creation order of published jobs
            metadata_json.sort(key=os.path.getmtime, reverse=True)

        with open(metadata_json[0]) as fp:
            job_info = json.load(fp)

        deadline_job_id = job_info["deadline_publish_job_id"]

        manager = ModulesManager()
        deadline_module = manager.modules_by_name["deadline"]
        deadline_url = deadline_module.deadline_urls["default"]

        if not deadline_url:
            raise ValueError("Must have default deadline url.")

        url = "{}/api/jobs?JobId={}".format(deadline_url, deadline_job_id)
        valid_date_finished = None

        time_start = time.time()
        while not valid_date_finished:
            time.sleep(0.5)
            if time.time() - time_start > timeout:
                raise ValueError("Timeout for DL finish reached")

            response = requests.get(url, timeout=10)
            if not response.ok:
                msg = "Couldn't connect to {}".format(deadline_url)
                raise RuntimeError(msg)

            if not response.json():
                raise ValueError("Couldn't find {}".format(deadline_job_id))

            # '0001-...' returned until job is finished
            valid_date_finished = response.json()[0]["DateComp"][:4] != "0001"

        # some clean exit test possible?
        print("Publish finished")
        yield True


class HostFixtures():
    """Host specific fixtures. Should be implemented once per host."""
    @pytest.fixture(scope="module")
    def last_workfile_path(self, download_test_data, output_folder_url):
        """Returns url of workfile"""
        raise NotImplementedError

    @pytest.fixture(scope="module")
    def startup_scripts(self, monkeypatch_session, download_test_data):
        """"Adds init scripts (like userSetup) to expected location"""
        raise NotImplementedError

    @pytest.fixture(scope="module")
    def skip_compare_folders(self):
        """Use list of regexs to filter out published folders from comparing"""
        raise NotImplementedError
