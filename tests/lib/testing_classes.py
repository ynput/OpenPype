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

from tests.lib.database_handler import DataBaseHandler
from common.ayon_common.distribution.file_handler import RemoteFileHandler
from openpype.modules import ModulesManager
from openpype.settings import get_project_settings


FILES = {
    "TestPublishInMaya": [
        ("1BTSIIULJTuDc8VvXseuiJV_fL6-Bu7FP", "test_maya_publish.zip", "")
    ]
}
DATABASE_PRODUCTION_NAME = "avalon_tests"
DATABASE_SETTINGS_NAME = "openpype_tests"

#needs testing
def download_test_data(data_folder, files):
    if data_folder:
        print("Using existing folder {}".format(data_folder))
        return data_folder

    data_folder = tempfile.mkdtemp()
    print("Temporary folder created:: {}".format(data_folder))
    for test_file in files:
        file_id, file_name, md5 = test_file

        f_name, ext = os.path.splitext(file_name)

        RemoteFileHandler.download_file_from_google_drive(
            file_id, str(data_folder), file_name
        )

        if ext.lstrip('.') in RemoteFileHandler.IMPLEMENTED_ZIP_FORMATS:
            RemoteFileHandler.unzip(os.path.join(data_folder, file_name))

    return data_folder

#needs testing
def output_folder(data_folder):
    path = os.path.join(data_folder, "output")
    if os.path.exists(path):
        print("Purging {}".format(path))
        shutil.rmtree(path)
    return path


def get_backup_directory(data_folder):
    return os.path.join(data_folder, "input", "dumps")

#needs testing
def database_setup(backup_directory, openpype_mongo):
    database_handler = DataBaseHandler(openpype_mongo)
    database_handler.setup_from_dump(
        DATABASE_PRODUCTION_NAME,
        backup_directory,
        overwrite=True,
        database_name_out=DATABASE_PRODUCTION_NAME
    )
    database_handler.setup_from_dump(
        DATABASE_SETTINGS_NAME,
        backup_directory,
        overwrite=True,
        database_name_out=DATABASE_SETTINGS_NAME
    )

    return database_handler

#needs testing
def dump_databases(database_urls, data_folder, openpype_mongo,):
    for database_url in database_urls:
        dump_database(database_url, data_folder, openpype_mongo)

#needs testing
def dump_database(database_url, data_folder, openpype_mongo,):
    database_handler = DataBaseHandler(openpype_mongo)
    database_name, database_collection = database_url.split(".")
    database_handler.backup_to_dump(
        database_name,
        os.path.join(get_backup_directory(data_folder), database_name),
        collection=database_collection,
        json=True
    )

#needs testing
def setup(class_names, data_folder, openpype_mongo):
    # Collect files to setup.
    files = {}
    for name in class_names:
        files[name] = FILES[name]

    if not class_names:
        files = FILES

    data_folders = []
    for class_name, class_files in files.items():
        data_folder = download_test_data(data_folder, class_files)
        data_folders.append(data_folder)
        output_folder(data_folder)
        database_setup(get_backup_directory(data_folder), openpype_mongo)

    # Feedback to user about data folders.
    print("Setup in folders:\n" + "\n".join(data_folders))


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
            environment_setup - sets env vars from input file
            database_setup - prepares avalon AND openpype DBs for testing from
                        binary dumps from input data
            dbcon - returns DBConnection to AvalonDB
            dbcon_openpype - returns DBConnection for OpenpypeMongoDB

    """
    PERSIST = False  # True to not purge temporary folder nor test DB

    OPENPYPE_MONGO = "mongodb://localhost:27017"

    PROJECT_NAME = "test_project"
    ASSET_NAME = "test_asset"
    TASK_NAME = "test_task"

    DATA_FOLDER = None
    INPUT_DUMPS = None
    INPUT_ENVIRONMENT_JSON = None

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
            self.PROJECT_NAME
        )

    @pytest.fixture(scope="module")
    def download_test_data(self, data_folder, persist, request):
        data_folder = download_test_data(
            data_folder or self.DATA_FOLDER, FILES[self.__class__.__name__]
        )

        yield data_folder

        persist = (persist or self.PERSIST or self.is_test_failed(request))
        if not persist:
            print("Removing {}".format(data_folder))
            shutil.rmtree(data_folder)

    @pytest.fixture(scope="module")
    def output_folder(self, download_test_data):
        """Returns location of published data, cleans it first if exists."""
        path = output_folder(download_test_data)
        yield path

    @pytest.fixture(scope="module")
    def input_environment_json(self, download_test_data):
        path = self.INPUT_ENVIRONMENT_JSON
        if path is None:
            path = os.path.join(
                download_test_data, "input", "env_vars", "env_var.json"
            )
        yield path

    @pytest.fixture(scope="module")
    def environment_setup(
        self,
        monkeypatch_session,
        download_test_data,
        openpype_mongo,
        input_environment_json
    ):
        """Sets temporary env vars from json file."""
        # Collect openpype mongo.
        if openpype_mongo:
            self.OPENPYPE_MONGO = openpype_mongo

        # Get class attributes for environment.
        attributes = {}
        for attribute in ModuleUnitTest.__dict__.keys():
            if attribute[:2] != '__':
                value = getattr(self, attribute)
                if not callable(value):
                    attributes[attribute] = value

        # Module attributes.
        attributes["DATABASE_PRODUCTION_NAME"] = DATABASE_PRODUCTION_NAME
        attributes["DATABASE_SETTINGS_NAME"] = DATABASE_SETTINGS_NAME

        if not os.path.exists(input_environment_json):
            raise ValueError(
                "Env variable file {} doesn't exist".format(input_environment_json)
            )

        env_dict = {}
        try:
            with open(input_environment_json) as json_file:
                env_dict = json.load(json_file)
        except ValueError:
            print("{} doesn't contain valid JSON")
            six.reraise(*sys.exc_info())

        for key, value in env_dict.items():
            value = value.format(**attributes)
            print("Setting {}:{}".format(key, value))
            monkeypatch_session.setenv(key, str(value))

        # Reset connection to openpype DB with new env var.
        import openpype.settings.lib as sett_lib
        sett_lib._SETTINGS_HANDLER = None
        sett_lib._LOCAL_SETTINGS_HANDLER = None
        sett_lib.create_settings_handler()
        sett_lib.create_local_settings_handler()

        import openpype
        openpype_root = os.path.dirname(os.path.dirname(openpype.__file__))

        monkeypatch_session.setenv("OPENPYPE_REPOS_ROOT", openpype_root)

        # for remapping purposes (currently in Nuke)
        monkeypatch_session.setenv("TEST_SOURCE_FOLDER", download_test_data)

    @pytest.fixture(scope="module")
    def database_dumps(self, download_test_data):
        path = (
            self.INPUT_DUMPS or
            get_backup_directory(download_test_data)
        )
        yield path

    @pytest.fixture(scope="module")
    def database_setup(
        self,
        database_dumps,
        openpype_mongo,
        request
    ):
        """Restore prepared MongoDB dumps into selected DB."""

        if openpype_mongo:
            self.OPENPYPE_MONGO = openpype_mongo

        database_handler = database_setup(
            database_dumps,
            self.OPENPYPE_MONGO
        )

        yield database_handler

        persist = self.PERSIST or self.is_test_failed(request)
        if not persist:
            database_handler.teardown(DATABASE_PRODUCTION_NAME)
            database_handler.teardown(DATABASE_SETTINGS_NAME)

    @pytest.fixture(scope="module")
    def dbcon(self, environment_setup, database_setup, output_folder):
        """Provide test database connection.

            Database prepared from dumps with 'database_setup' fixture.
        """
        from openpype.pipeline import AvalonMongoDB
        dbcon = AvalonMongoDB()
        dbcon.Session["AVALON_PROJECT"] = self.PROJECT_NAME
        dbcon.Session["AVALON_ASSET"] = self.ASSET_NAME
        dbcon.Session["AVALON_TASK"] = self.TASK_NAME

        # set project root to temp folder
        platform_str = platform.system().lower()
        root_key = "config.roots.work.{}".format(platform_str)
        dbcon.update_one(
            {"type": "project"},
            {"$set":
                {
                    root_key: output_folder
                }}
        )
        yield dbcon

    @pytest.fixture(scope="module")
    def dbcon_openpype(self, environment_setup, database_setup):
        """Provide test database connection for OP settings.

            Database prepared from dumps with 'database_setup' fixture.
        """
        from openpype.lib import OpenPypeMongoConnection
        mongo_client = OpenPypeMongoConnection.get_mongo_client()
        yield mongo_client[self.DATABASE_SETTINGS_NAME]["settings"]

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
    DATA_FOLDER = None  # use specific folder of unzipped test file

    SETUP_ONLY = False

    @pytest.fixture(scope="module")
    def app_name(self, environment_setup, app_variant):
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
    def launched_app(
        self,
        dbcon,
        download_test_data,
        last_workfile_path,
        startup_scripts,
        app_args,
        app_name,
        output_folder,
        keep_app_open
    ):
        """Launch host app"""
        # set schema - for integrate_new
        from openpype import PACKAGE_DIR
        # Path to OpenPype's schema
        schema_path = os.path.join(
            os.path.dirname(PACKAGE_DIR),
            "schema"
        )
        os.environ["AVALON_SCHEMA"] = schema_path

        os.environ["OPENPYPE_EXECUTABLE"] = sys.executable

        if keep_app_open:
            os.environ["KEEP_APP_OPEN"] = "1"

        from openpype.lib import ApplicationManager

        application_manager = ApplicationManager()
        data = {
            "last_workfile_path": last_workfile_path,
            "start_last_workfile": True,
            "project_name": self.PROJECT_NAME,
            "asset_name": self.ASSET_NAME,
            "task_name": self.TASK_NAME
        }
        if app_args:
            data["app_args"] = app_args

        app_process = application_manager.launch(app_name, **data)
        yield app_process

    @pytest.fixture(scope="module")
    def publish_finished(
        self,
        dbcon,
        launched_app,
        download_test_data,
        timeout,
        keep_app_open
    ):
        """Dummy fixture waiting for publish to finish"""
        import time
        time_start = time.time()
        timeout = timeout or self.TIMEOUT

        if keep_app_open:
            timeout = 100000

        timeout = float(timeout)
        while launched_app.poll() is None:
            time.sleep(0.5)
            if time.time() - time_start > timeout:
                launched_app.terminate()
                raise ValueError("Timeout reached")

        # some clean exit test possible?
        print("Publish finished")
        yield True

    def test_folder_structure_same(
        self,
        dbcon,
        publish_finished,
        download_test_data,
        output_folder,
        skip_compare_folders
    ):
        """Check if expected and published subfolders contain same files.

            Compares only presence, not size nor content!
        """
        published_dir_base = output_folder
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
    def last_workfile_path(self, download_test_data, output_folder):
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
