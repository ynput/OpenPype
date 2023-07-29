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
import subprocess

from tests.lib.database_handler import DataBaseHandler
from common.ayon_common.distribution.file_handler import RemoteFileHandler
from openpype.modules import ModulesManager
from openpype.settings import get_project_settings


def get_database_names():
    return {
        "production": "avalon_tests",
        "settings": "openpype_tests"
    }


def get_database_sufficed(suffix):
    result = {}
    for key, value in get_database_names().items():
        result[key] = "{}_{}".format(value, suffix)
    return result


#needs testing
def setup_data_folder(data_folder, files):
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
def setup_output_folder(data_folder, app_variant):
    path = os.path.join(data_folder, "output_" + app_variant)
    if os.path.exists(path):
        print("Purging {}".format(path))
        shutil.rmtree(path)
    return path


def get_backup_directory(data_folder):
    return os.path.join(data_folder, "input", "dumps")

#needs testing
def setup_database(backup_directory, openpype_mongo, suffix):
    database_handler = DataBaseHandler(openpype_mongo)
    database_names = get_database_names()

    database_handler.setup_from_dump(
        database_names["production"],
        backup_directory,
        "_" + suffix,
        overwrite=True,
        database_name_out=database_names["production"]
    )
    database_handler.setup_from_dump(
        database_names["settings"],
        backup_directory,
        "_" + suffix,
        overwrite=True,
        database_name_out=database_names["settings"]
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


class BaseTest:
    """Empty base test class"""


class ModuleUnitTest(BaseTest):
    """Generic test class for testing modules

        Use PERSIST==True to keep temporary folder and DB prepared for
        debugging or preparation of test files.

        Implemented fixtures:
            monkeypatch_session - fixture for env vars with session scope
            project_settings - fixture for project settings with session scope
            setup_fixture - tmp folder with extracted data from GDrive
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

    #needs testing.
    def setup_only(self, data_folder, openpype_mongo, app_variant):
        data_folder = setup_data_folder(data_folder, self.FILES)
        output_folder = setup_output_folder(data_folder, app_variant)
        database_handler = setup_database(
            self.INPUT_DUMPS or get_backup_directory(data_folder),
            openpype_mongo,
            app_variant
        )

        return data_folder, output_folder, database_handler

    @pytest.fixture(scope="module")
    def setup_fixture(
        self, data_folder, openpype_mongo, app_variant, persist, request
    ):
        data_folder, output_folder, database_handler = self.setup_only(
            data_folder, openpype_mongo, app_variant
        )

        yield data_folder, output_folder, database_handler

        persist = (persist or self.PERSIST or self.is_test_failed(request))
        if not persist:
            print("Removing {}".format(data_folder))
            shutil.rmtree(data_folder)

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
    def input_environment_json(self, setup_fixture):
        data_folder, _, _ = setup_fixture
        path = self.INPUT_ENVIRONMENT_JSON
        if path is None:
            path = os.path.join(
                data_folder, "input", "env_vars", "env_var.json"
            )
        yield path

    @pytest.fixture(scope="module")
    def environment_setup(
        self,
        monkeypatch_session,
        setup_fixture,
        openpype_mongo,
        input_environment_json,
        app_variant
    ):
        """Sets temporary env vars from json file."""
        data_folder, _, _ = setup_fixture

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
        database_names = get_database_sufficed(app_variant)
        attributes["DATABASE_PRODUCTION_NAME"] = database_names["production"]
        attributes["DATABASE_SETTINGS_NAME"] = database_names["settings"]

        if not os.path.exists(input_environment_json):
            raise ValueError(
                "Env variable file {} doesn't exist".format(
                    input_environment_json
                )
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
        monkeypatch_session.setenv("TEST_SOURCE_FOLDER", data_folder)

    @pytest.fixture(scope="module")
    def database_dumps(self, setup_fixture):
        path = (
            self.INPUT_DUMPS or
            get_backup_directory(setup_fixture)
        )
        yield path

    @pytest.fixture(scope="module")
    def dbcon(self, environment_setup, setup_fixture):
        """Provide test database connection.

            Database prepared from dumps with 'database_setup' fixture.
        """
        _, output_folder, _ = setup_fixture

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
    def dbcon_openpype(self, environment_setup, setup_fixture, app_variant):
        """Provide test database connection for OP settings.

            Database prepared from dumps with 'database_setup' fixture.
        """
        from openpype.lib import OpenPypeMongoConnection
        mongo_client = OpenPypeMongoConnection.get_mongo_client()
        database_names = get_database_sufficed(app_variant)
        yield mongo_client[database_names["settings"]]["settings"]

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

    def app_variants(self, app_group, app_variant):
        app_variants = []

        from openpype.lib import ApplicationManager
        app_group = app_group or self.APP_GROUP

        application_manager = ApplicationManager()

        if app_variant == "*":
            func = application_manager.find_all_available_variants_for_group
            variants = func(app_group)
            app_variants = [x.name for x in variants]

        if app_variant is None or not app_variant:
            func = application_manager.find_latest_available_variant_for_group
            variant = func(app_group)
            app_variants.append(variant.name)

        if app_variant:
            app_variants.append(app_variant)

        return app_variants

    @pytest.fixture(scope="module")
    def app_name(self, environment_setup, app_variant, app_group):
        """Returns calculated value for ApplicationManager. Eg.(nuke/12-2)"""
        from openpype.lib import ApplicationManager
        app_variant = app_variant or self.APP_VARIANT
        app_group = app_group or self.APP_GROUP

        application_manager = ApplicationManager()
        if not app_variant:
            variant = (
                application_manager.find_latest_available_variant_for_group(
                    app_group
                )
            )
            app_variant = variant.name

        yield "{}/{}".format(app_group, app_variant)

    @pytest.fixture(scope="module")
    def app_args(self, setup_fixture):
        """Returns additional application arguments from a test file.

            Test zip file should contain file at:
                FOLDER_DIR/input/app_args/app_args.json
            containing a list of command line arguments (like '-x' etc.)
        """
        data_folder, _, _ = setup_fixture
        app_args = []
        args_url = os.path.join(
            data_folder, "input", "app_args", "app_args.json"
        )
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
    def start_last_workfile(self):
        """Returns url of workfile"""
        return True

    @pytest.fixture(scope="module")
    def launched_app(
        self,
        dbcon,
        setup_fixture,
        last_workfile_path,
        start_last_workfile,
        startup_scripts,
        app_args,
        app_name,
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
            "start_last_workfile": start_last_workfile,
            "project_name": self.PROJECT_NAME,
            "asset_name": self.ASSET_NAME,
            "task_name": self.TASK_NAME,
            "stdout": subprocess.PIPE
        }
        if app_args:
            data["app_args"] = app_args

        print("Launching {} with {}".format(app_name, data))
        app_process = application_manager.launch(app_name, **data)
        yield app_process

    @pytest.fixture(scope="module")
    def publish_finished(
        self,
        dbcon,
        launched_app,
        setup_fixture,
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
            out, err = launched_app.communicate()
            time.sleep(0.5)
            if time.time() - time_start > timeout:
                launched_app.terminate()
                raise ValueError("Timeout reached")

        # some clean exit test possible?
        print("Publish finished")
        yield out.decode("utf-8")

    def test_folder_structure_same(
        self,
        dbcon,
        publish_finished,
        setup_fixture,
        skip_compare_folders
    ):
        """Check if expected and published subfolders contain same files.

            Compares only presence, not size nor content!
        """
        data_folder, output_folder, _ = setup_fixture
        expected_dir_base = os.path.join(data_folder, "expected")

        print("Comparing published:'{}' : expected:'{}'".format(
            output_folder, expected_dir_base))
        published = set(f.replace(output_folder, '') for f in
                        glob.glob(output_folder + "\\**", recursive=True)
                        if f != output_folder and os.path.exists(f))
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
    def publish_finished(self, dbcon, launched_app, setup_fixture,
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

        metadata_json = glob.glob(os.path.join(setup_fixture,
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
    def last_workfile_path(self, setup_fixture, output_folder):
        """Returns url of workfile"""
        raise NotImplementedError

    @pytest.fixture(scope="module")
    def startup_scripts(self, monkeypatch_session, setup_fixture):
        """"Adds init scripts (like userSetup) to expected location"""
        raise NotImplementedError

    @pytest.fixture(scope="module")
    def skip_compare_folders(self):
        """Use list of regexs to filter out published folders from comparing"""
        raise NotImplementedError
