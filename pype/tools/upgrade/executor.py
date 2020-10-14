from pype.api import Logger
import os
import pyclbr
from pype.mongodb import PypeMongoDB
from avalon.api import AvalonMongoDB
from datetime import datetime, timezone
import importlib
import sys
from bson import objectid
import contextlib
import pymongo.errors

# keep it here for correct initialization of patches #TODO refactor
from pype.tools.upgrade.patches.abtract_patch import AbstractPatch

log = Logger().get_logger("UpgradeExecutor")


class UpgradeExecutor:
    """
        Should be run by trigger or at start of Pype to check if any not
        implemented updates (database or APIs) exist.
        Useful for more automatic upgrade process.
    """
    DB_PATCHES_DIR = os.path.join(os.path.dirname(__file__), 'patches')
    SKIP_PATCHES = []

    def __init__(self, patches_dir=None, skip_patches=None, projects=None):
        """
            Initialize upgrade run
        Args:
            patches_dir (string): absolute path to folder with patches
            skip_patches (list): of strings of patch names (file name without
                extension) that should be skipped
            projects (list): of strings of project names (eg. collection names)
        """
        if patches_dir:  # for testing
            self.DB_PATCHES_DIR = patches_dir

        self.projects = []
        if projects:
            self.projects = list(projects)

        # list of patches to be skipped - for testing mostly
        self.SKIP_PATCHES = skip_patches or []

        self.conn = PypeMongoDB("upgrade_patches")
        self.conn.install()

        self.avalon_conn = AvalonMongoDB()
        self.avalon_conn.install()

        self.something_updated = False
        self.avalon_transaction_enabled = self._is_replica_set(
            self.avalon_conn)
        self.pype_transaction_enabled = self._is_replica_set(self.conn)

        self.execute()

    def execute(self):
        """ Main function """
        patches = self.get_patches(self.DB_PATCHES_DIR)
        for patch_name in patches:
            if patch_name in self.SKIP_PATCHES:
                continue

            if not self._is_real_patch(patch_name):
                continue

            self.lock()

            patch = self.get_patch(patch_name, self.avalon_conn, self.conn)

            log_record = self.get_implemented_patch_report(patch.name)

            if not log_record:
                mongo_id = self.report_to_db(patch.get_report_record_base())
            else:
                mongo_id = log_record["_id"]
            with patch.avalon_session as av_s, patch.pype_session as py_s:
                # transactions are enabled only on replica sets
                # double check if have RS >> start transaction,
                # use dummmy otherwise
                with av_s.start_transaction() \
                        if self.avalon_transaction_enabled \
                        else dummy__mgr() as at, \
                     py_s.start_transaction() \
                        if self.pype_transaction_enabled \
                        else dummy__mgr() as pt:

                    if patch.is_affected('global') and \
                            not self.is_applied_on(log_record, 'global'):
                        self.process_patch(mongo_id, patch,
                                           'global',
                                           log_record)

                    if patch.is_affected('project'):
                        if self.projects:  # manual run on selected project(s)
                            for project_name in self.projects:
                                self.process_patch(mongo_id, patch,
                                                   project_name,
                                                   log_record)
                        else:
                            for project in self.avalon_conn.projects():
                                project_name = project["name"]
                                self.process_patch(mongo_id, patch,
                                                   project_name,
                                                   log_record)

        if not self.something_updated:
            raise ValueError("Nothing updated, no updatable areas found.")

        self.unlock()

    def process_patch(self, mongo_id, patch, label, log_record):
        """
            Checks if 'patch' could be run on 'label', runs it and
            stores result in DB.
        Args:
            mongo_id (ObjectId): report document from MongoDB
            patch (AbstractPatch):
            label (string): 'global' or 'project_A'
            log_record (dict): log document from Mongo

        Raises:
            (ValueError)

        """
        if label != 'global' and self.is_upgradable(patch, label, log_record):
            result, error_message = patch.run_on_project(label)
        else:
            result, error_message = patch.run_global()

        self.something_updated = True
        applied_on = {label: datetime.now(timezone.utc)}
        self.update_report(mongo_id, error_message, applied_on=applied_on)
        if not result:
            raise ValueError(error_message)

        log.debug("Ran {} for {} section".format(patch.name, label))

    def get_patch(self, patch_name, avalon_conn, pype_conn):
        """
            Get patch object.
            Dynamically imports patch class with 'patch_name'
        Args:
            patch_name (string):

        Returns:
            (AbstractPatch)
        """
        log.debug('----{}----'.format(patch_name))

        module_info = pyclbr.readmodule(patch_name, [self.DB_PATCHES_DIR])
        patch = None
        for class_name, cls_object in module_info.items():
            if 'AbstractPatch' in cls_object.super:
                sys.path.append(self.DB_PATCHES_DIR)
                module = importlib.import_module(patch_name)
                cls = getattr(module, class_name)
                # initialize patch class
                patch = cls(avalon_connection=avalon_conn,
                            pype_connection=pype_conn)
                sys.path.pop()
                return patch

        return patch

    def _is_real_patch(self, patch_name):
        """
            Check if 'patch_name' implements
        Args:
            patch_name:

        Returns:

        """
        module_info = pyclbr.readmodule(patch_name, [self.DB_PATCHES_DIR])
        for _, cls_object in module_info.items():
            if 'AbstractPatch' in cls_object.super:
                return True

        return False

    def get_patches(self, dir_name):
        """
            Lists all files in 'dir_name' and returns list of names of
            python files
        Args:
            dir_name:

        Returns:
            (list) names of python files (without extension)
        """
        patches = []
        for file_name in os.listdir(dir_name):
            if '.py' in file_name and '__' not in file_name:
                patches.append(file_name.replace('.py', ''))

        return sorted(patches)

    def get_implemented_patches(self):
        """
            Returns all documents about finished patches.
        Returns:
            (dictionary) {'patch_name': ['project_A', 'project_B']}
        """
        return [self.conn.database.upgrade_patches.find({}, {})]

    def get_implemented_patch_report(self, patch_name):
        """
            Return active log document for 'patch_name'.
            Active means that previous run of the patch didn't failed.
            There is single report document for whole patch which gets updated
            if patch:
                is triggered multiple times for selected projects (testing)
                contains multiple targets ('global', 'project'...)
        Args:
            patch_name (string):

        Returns:
            (dictionary) from Mongo | None if not found
        """
        filter = {'name': patch_name, "error_message": {"$exists": False}}
        return self.conn.database.upgrade_patches.find_one(filter)

    def is_locked(self):
        """
            Checks database for presence of lock record.
        Returns:
            (boolean): true if lock record
        """
        lock_record_count = self.conn.database.upgrade_patches. \
            count_documents({"type": "lock"})

        return lock_record_count > 0

    def lock(self):
        """
            Creates lock record in DB. If already present, raises error.
            Created_dt in UTC.
        Raises:
            (ValueError)
        """
        if self.is_locked():
            raise ValueError("Already locked. Remove lock record manually.")
        lock_record = {"type": "lock", "start_dt": datetime.now(timezone.utc)}

        self.conn.database.upgrade_patches.insert_one(lock_record)

    def unlock(self):
        """
            Removes lock record in DB if present
        """
        self.conn.database.upgrade_patches.remove({"type": "lock"})

    def report_to_db(self, report):
        """
            Creates report record in 'pype' db.
        Args:
            report (dictionary): skeleton of reporting record (with version,
                affects, description etc.

        Returns:
            (ObjectId)
        """
        return self.conn.database.upgrade_patches.insert(report)

    def update_report(self, mongo_id, error_message='', applied_on=None,
                      options=None):
        """
            Updates log report in db for particular patch
        Args:
            mongo_id (ObjectId): report document in MongoDB
            error_message (string):
            applied_on (dict): 'global': 'DDMMYYYY hh:mm:ss' when area was
                updated
            options (dict): additional info about patch run (did it save to db)

        """
        filter = {"_id": objectid.ObjectId(mongo_id)}
        report = self.conn.database.upgrade_patches.find_one(filter)
        if not report:
            raise ValueError("Report document {} not found".format(mongo_id))

        if error_message:
            report["error_message"] = error_message

        if options:
            for key, value in options.items():
                report[key] = value

        if applied_on:
            rec_applied = report.get("applied_on", {})
            for key, value in applied_on.items():
                if key in rec_applied.keys():
                    report["error_message"] += " Double application of {}".\
                        format(key)
                    break

                rec_applied[key] = value
            report["applied_on"] = rec_applied

        self.conn.database.upgrade_patches.update(filter, report, upsert=True)

    def is_upgradable(self, patch, project_name, log_record):
        """
            Checks if 'patch' should be triggered on 'project_name'
        Args:
            patch (AbstractPatch):
            project_name (string):
            log_record (dictionary): logging document from Mongo

        Returns:
            (bool)
        """
        return not self.is_applied_on(log_record, project_name) \
            and not self.is_project_frozen(project_name) \
            and self.is_version_applicable(project_name, patch.version)

    def is_applied_on(self, log_record, label):
        """
            Check if 'label' was already applied for this patch 'log_record'
        Args:
            log_record (dict): from Mongo
            label (string): 'global'|'project_A'

        Returns:
            (bool)
        """
        ret = False
        if log_record and log_record["applied_on"]:
            ret = log_record["applied_on"].get(label, False)
        return ret

    def is_project_frozen(self, project_name):
        """
            Check if 'project_name' is frozen, eg. shouldn't be updated at all
        Args:
            project_name (string):

        Returns:
            (bool)
        Raises:
            ValueError if project wasn't found
        """
        return self._get_project(project_name).get("freeze", False)

    def is_version_applicable(self, project_name, version):
        """
            Check if version of the patch is bigger than version of the project
            Other case would mean that patch is for this particular project
            obsolete. Project was created in newer version, with newer
            structure.
        Args:
            project_name (string):
            version (string): "2.13.0"

        Returns:
            (bool)

        """
        project_version = self._get_project(project_name).get("version",
                                                              "0.0.0")
        return version > project_version

    def _get_project(self, project_name):
        """
            Return project object by its name

        Args:
            project_name(string):
        Returns:
            (dictionary) - project object
        Raises:
            ValueError if project wasn't found
        """
        for project in self.avalon_conn.projects():
            if project["name"] == project_name:
                return project

        raise ValueError("Project {} not found!".format(project_name))

    def _is_replica_set(self, conn):
        """
            Weird way to check if host of connection is replica set >> allows
            transactions
        Args:
            conn (AvalonMongoDB|PypeMongoDB):

        Returns:
            (bool)
        """
        is_replica_set = False
        try:
            conn.mongo_client.admin.command("replSetGetStatus")
            is_replica_set = True
        except pymongo.errors.OperationFailure as exp:
            pass

        return is_replica_set

@contextlib.contextmanager
def dummy__mgr():
    yield None
