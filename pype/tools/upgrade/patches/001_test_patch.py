from pype.tools.upgrade.patches.abtract_patch import AbstractPatch
from pype.api import Logger
import traceback

log = Logger().get_logger("UpgradeExecutor")


class TestPatch(AbstractPatch):
    """ Test implementation of patch """
    def __init__(self, avalon_connection=None, pype_connection=None):
        log.debug("init TestPatch")

        self.avalon_db = avalon_connection
        self.pype_db = pype_connection

    def update_avalon_global(self):
        log.debug("TestPatch.update_avalon_global")
        return True

    def update_avalon_project(self, project_name):
        log.debug("TestPatch.update_avalon_project")
        # new_object = {"name": "test_object"}
        # try:
        #     self.avalon_db.database.project_name.insert_one(new_object)
        # except:
        #     log.warning(
        #         "Error has happened during update_pype_db",
        #         exc_info=True
        #     )
        #     return False, traceback.format_exception_only

        return True, ''

    def update_api(self, api):
        log.debug("TestPatch.update_avalon_global")
        return True

    def update_pype_db(self):
        log.debug("TestPatch.update_pype_db")
        new_object = {"name": "test_object"}

        try:
            self.pype_db.database.upgrade_patches.insert_one(new_object)
        except:
            log.warning(
                "Error has happened during update_pype_db",
                exc_info=True
            )
            return False, traceback.format_exception_only

        return True, ''

    def run(self, projects=[]):
        log.debug("run TestPatch")
        result, error = self.update_pype_db()
        if result:
            for project_name in projects:
                self.update_avalon_project(project_name)

        return result, error

