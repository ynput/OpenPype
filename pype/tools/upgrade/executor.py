from pype.api import Logger
import os
import pyclbr
from pype.mongodb import PypeMongoDB
from datetime import datetime, timezone
import importlib
import sys
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

        implemented_patches = self.get_implemented_patches()
        log.debug("implemented_patches::{}".format(len(implemented_patches)))

        for patch_name in patches:
            if patch_name not in implemented_patches:
                if self.is_locked():
                    raise ValueError("System should be upgraded, but already "
                                     "locked! Remove lock from DB.")
                result, error_message = self.run_patch(patch_name)
                self.report_to_db(patch_name, error_message)
                log.debug("result {}, error_message {}".format(result,
                                                               error_message))
                if not result:
                    raise ValueError("Patch {} failed".format(patch_name))

    def run_patch(self, patch_name):
        """
            Checks if 'patch_name' implements 'AbstractPatch', triggers its
            'run' method and returns result tuple
        Args:
            patch_name (string): file name of patch (without extension)

        Returns:
            (boolean, string): true if all OK, (false, error_message) otherwise
        """
        log.debug('----{}----'.format(patch_name))
        patch_url = os.path.join(self.DB_PATCHES_DIR, patch_name + ".py")

        module_info = pyclbr.readmodule(patch_name, [self.DB_PATCHES_DIR])
        result = False
        error_message = ''
        for class_name, cls_object in module_info.items():
            if 'AbstractPatch' in cls_object.super:
                sys.path.append(self.DB_PATCHES_DIR)
                module = importlib.import_module(patch_name)
                cls = getattr(module, class_name)
                # initialize patch class
                patch = cls(pype_connection=self.conn)
                log.debug("Run {}".format(patch_name))
                # run patch
                result, error_message = patch.run(projects=['petr_test'])
                sys.path.pop()

        return result, error_message

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

    def report_to_db(self, patch_name, error_message='', options={}):
        """
            Creates log report in db for particular patch
        Args:
            patch_name (string):
            error_message (string):
            options (dict): additional info about patch run (did it save to db)

        """
        report = {
            "patch_name": patch_name,
            "finished_dt": datetime.now(timezone.utc)
        }
        if error_message:
            report["error_message"] = error_message

        for key, value in options:
            report[key] = value

        self.conn.database.upgrade_patches.insert_one(report)
