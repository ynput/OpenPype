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
import zipfile
import time

from tests.lib.database_handler import DataBaseHandler
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

    EXPECTED_FOLDER = None
    DATA_FOLDER = None
    INPUT_DUMPS = None
    INPUT_ENVIRONMENT_JSON = None
    INPUT_WORKFILE = None

    FILES = []

    DATABASE_NAMES = {
        "production": {
            "name": "avalon_tests",
            "collections": [PROJECT_NAME]
        },
        "settings": {
            "name": "openpype_tests",
            "collections": []
        }
    }

    def get_backup_directory(self, data_folder):
        return os.path.join(data_folder, "input", "dumps")

    #needs testing
    @classmethod
    def setup_only(cls, data_folder, openpype_mongo, app_variant):
        if data_folder:
            print("Using existing folder {}".format(data_folder))

            # Check root folder exists else extract from zip. This allows for
            # testing with WIP zips locally.
            for _, file_name, _ in cls.FILES:
                file_path = os.path.join(data_folder, file_name)
                if os.path.exists(file_path):
                    zip = zipfile.ZipFile(file_path)

                    # Get all root folders and check against existing folders.
                    root_folder_names = [
                        x for x in zip.namelist() if len(x.split("/")) == 2
                    ]
                    for name in root_folder_names:
                        path = os.path.join(data_folder, name[:-1])
                        if os.path.exists(path):
                            continue

                        for zip_name in zip.namelist():
                            if zip_name.startswith(name):
                                zip.extract(zip_name, data_folder)
        else:
            data_folder = tempfile.mkdtemp()
            print("Temporary folder created: {}".format(data_folder))
            for test_file in cls.FILES:
                file_id, file_name, md5 = test_file

                f_name, ext = os.path.splitext(file_name)

                RemoteFileHandler.download_file_from_google_drive(
                    file_id, str(data_folder), file_name
                )

                zip_formats = RemoteFileHandler.IMPLEMENTED_ZIP_FORMATS
                if ext.lstrip(".") in zip_formats:
                    RemoteFileHandler.unzip(
                        os.path.join(data_folder, file_name)
                    )

        output_folder = os.path.join(data_folder, "output_" + app_variant)
        if os.path.exists(output_folder):
            print("Purging {}".format(output_folder))
            shutil.rmtree(output_folder)

        database_handler = DataBaseHandler(openpype_mongo)
        backup_directory = (
            cls.INPUT_DUMPS or cls.get_backup_directory(cls, data_folder)
        )

        for _, data in cls.DATABASE_NAMES.items():
            if not data["collections"]:
                continue

            database_handler.setup_from_dump(
                data["name"],
                backup_directory,
                "_" + app_variant,
                overwrite=True,
                database_name_out=data["name"]
            )

        return data_folder, output_folder, database_handler

    #needs testing
    @classmethod
    def dump_databases(cls, data_folder, openpype_mongo, app_variant):
        database_handler = DataBaseHandler(openpype_mongo)
        dumps_folder = (
            cls.INPUT_DUMPS or
            os.path.join(
                cls.get_backup_directory(data_folder), "inputs", "dumps"
            )
        )
        for _, data in cls.DATABASE_NAMES.items():
            for collection in data["collections"]:
                database_handler.backup_to_dump(
                    "{}_{}".format(data["name"], app_variant),
                    os.path.join(dumps_folder, data["name"]),
                    collection=collection,
                    json=True,
                    filename="{}.{}.json".format(data["name"], collection)
                )

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

    @pytest.fixture(scope="session")
    def monkeypatch_session(self):
        """Monkeypatch couldn't be used with module or session fixtures."""
        from _pytest.monkeypatch import MonkeyPatch
        m = MonkeyPatch()
        yield m
        m.undo()

    @pytest.fixture(scope="module")
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
            if attribute[:2] != "__":
                value = getattr(self, attribute)
                if not callable(value):
                    attributes[attribute] = value

        # Module attributes.
        for database_type, data in self.DATABASE_NAMES.items():
            attr = "DATABASE_{}_NAME".format(database_type.upper())
            attributes[attr] = "{}_{}".format(data["name"], app_variant)

        if not os.path.exists(input_environment_json):
            raise ValueError(
                "Env variable file {} doesn't exist".format(
                    input_environment_json
                )
            )
        print("Loading " + input_environment_json)
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
            self.get_backup_directory(setup_fixture)
        )
        yield path

    @pytest.fixture(scope="module")
    def dbcon(self, environment_setup, setup_fixture):
        """Provide test database connection.

            Database prepared from dumps with "database_setup" fixture.
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

            Database prepared from dumps with "database_setup" fixture.
        """
        from openpype.lib import OpenPypeMongoConnection
        mongo_client = OpenPypeMongoConnection.get_mongo_client()
        database_names = self.get_database_sufficed(app_variant)
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

    TIMEOUT = 240  # publish timeout

    # could be overwritten by command line arguments
    # command line value takes precedence

    # keep empty to locate latest installed variant or explicit
    APP_VARIANT = ""
    PERSIST = True  # True - keep test_db, test_openpype, outputted test files
    DATA_FOLDER = None  # use specific folder of unzipped test file

    def app_variants(self, app_group, app_variant):
        app_variants = []

        from openpype.lib import ApplicationManager
        app_group = app_group or self.APP_GROUP

        application_manager = ApplicationManager()

        if app_variant == "all":
            func = application_manager.find_all_available_variants_for_group
            variants = func(app_group)
            app_variants = [x.name for x in variants]

        if app_variant is None or not app_variant:
            func = application_manager.find_latest_available_variant_for_group
            variant = func(app_group)
            app_variants.append(variant.name)

        if app_variant and app_variant != "all":
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
            containing a list of command line arguments (like "-x" etc.)
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
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE
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

        print("Publish finished")

        msg = "Launched app errored:\n{}"
        assert launched_app.returncode == 0, msg.format(err.decode("utf-8"))

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
        expected_dir_base = self.EXPECTED_FOLDER
        if expected_dir_base is None:
            expected_dir_base = os.path.join(data_folder, "expected")

        print("Comparing published:'{}' : expected:'{}'".format(
            output_folder, expected_dir_base))
        published = set(f.replace(output_folder, "") for f in
                        glob.glob(output_folder + "\\**", recursive=True)
                        if f != output_folder and os.path.exists(f))
        expected = set(f.replace(expected_dir_base, "") for f in
                       glob.glob(expected_dir_base + "\\**", recursive=True)
                       if f != expected_dir_base and os.path.exists(f))

        filtered_published = self._filter_files(published,
                                                skip_compare_folders)

        # filter out temp files also in expected
        # could be polluted by accident by copying "output" to zip file
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

    @pytest.fixture(scope="module")
    def deadline_finished(
        self,
        dbcon,
        launched_app,
        setup_fixture,
        timeout,
        publish_finished,
        app_variant
    ):
        """Dummy fixture waiting for publish to finish"""

        data_folder, _, _ = setup_fixture

        metadata_json = glob.glob(
            os.path.join(
                data_folder, "output_" + app_variant, "**/*_metadata.json"
            ),
            recursive=True
        )
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
        timeout = timeout or self.TIMEOUT
        while not valid_date_finished:
            time.sleep(0.5)
            if time.time() - time_start > timeout:
                raise ValueError("Timeout for Deadline finish reached")

            response = requests.get(url, timeout=10)
            if not response.ok:
                msg = "Couldn't connect to {}".format(deadline_url)
                raise RuntimeError(msg)

            if not response.json():
                raise ValueError("Couldn't find {}".format(deadline_job_id))

            errors = []
            resp_error = requests.get(
                "{}/api/jobreports?JobID={}&Data=allerrorcontents".format(
                    deadline_url, deadline_job_id
                ),
                timeout=10
            )
            errors.extend(resp_error.json())
            for dependency in response.json()[0]["Props"]["Dep"]:
                resp_error = requests.get(
                    "{}/api/jobreports?JobID={}&Data=allerrorcontents".format(
                        deadline_url, dependency["JobID"]
                    ),
                    timeout=10
                )
                errors.extend(resp_error.json())

            msg = "Errors in Deadline:\n"
            msg += "\n".join(errors)
            assert not errors, msg

            # "0001-..." returned until job is finished
            valid_date_finished = response.json()[0]["DateComp"][:4] != "0001"


class HostFixtures():
    """Host specific fixtures. Should be implemented once per host."""
    @pytest.fixture(scope="module")
    def last_workfile_path(self, setup_fixture):
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
