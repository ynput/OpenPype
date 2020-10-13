from pype.api import Logger
import os
import pyclbr
from pype.mongodb import PypeMongoDB
from avalon.api import AvalonMongoDB
from datetime import datetime, timezone
import importlib
import sys
from bson import objectid

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

    def __init__(self, patches_dir=None, skip_patches=None):
        if patches_dir:  # for testing
            self.DB_PATCHES_DIR = patches_dir

        # list of patches to be skipped - for testing mostly
        self.SKIP_PATCHES = skip_patches or []

        patches = self.get_patches(self.DB_PATCHES_DIR)
        log.debug("patches::{}".format(patches))

        self.conn = PypeMongoDB("upgrade_patches")
        log.debug("connection {}".format(self.conn))

        self.avalon_conn = AvalonMongoDB()
        self.avalon_conn.install()

        implemented_patches = self.get_implemented_patches()
        log.debug("implemented_patches::{}".format(len(implemented_patches)))

        for patch_name in patches:

            if patch_name not in implemented_patches and \
                    self._is_real_patch(patch_name):
                if self.is_locked():
                    raise ValueError("System should be upgraded, but already "
                                     "locked! Remove lock from DB.")

                patch = self.get_patch(patch_name)
                mongo_id = self.report_to_db(patch.get_report_record_base())
                result, error_message = patch.run()
                self.update_report(mongo_id, error_message)
                log.debug("result {}, error_message {}".format(result,
                                                               error_message))
                if not result:
                    raise ValueError("Patch {} failed".format(patch_name))

    def get_patch(self, patch_name):
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
            log.debug("cls_object.super:: {}".format(cls_object.super))
            if 'AbstractPatch' in cls_object.super:
                sys.path.append(self.DB_PATCHES_DIR)
                module = importlib.import_module(patch_name)
                cls = getattr(module, class_name)
                # initialize patch class
                patch = cls(avalon_connection=self.avalon_conn,
                            pype_connection=self.conn)
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
        for class_name, cls_object in module_info.items():
            log.debug("cls_object.super:: {}".format(cls_object.super))
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
            (list) of documents
        """
        return [self.conn.database.upgrade_patches.find()]

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

    def update_report(self, mongo_id, error_message='', options={}):
        """
            Updates log report in db for particular patch
        Args:
            mongo_id (ObjectId):
            error_message (string):
            options (dict): additional info about patch run (did it save to db)

        """
        filter = {"_id": objectid.ObjectId(mongo_id)}
        report = self.conn.database.upgrade_patches.find_one(filter)
        if not report:
            raise ValueError("Report document {} not found".format(mongo_id))

        if error_message:
            report["error_message"] = error_message

        log.debug("options {}".format(options))
        for key, value in options:
            report[key] = value

        log.debug("report {}".format(report))

        self.conn.database.upgrade_patches.update(filter, report, upsert=True)
