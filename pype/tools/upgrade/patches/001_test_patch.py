from pype.tools.upgrade.patches.abtract_patch import AbstractPatch
from pype.api import Logger

log = Logger().get_logger("UpgradeExecutor")


class TestPatch(AbstractPatch):
    # implemented this way to reuse properties from AbstractPatch
    version = "1.0.0"
    affects = ["avalon_db", "pype_db"]
    description = {"avalon_db": "Test avalon db patch",
                   "pype_db": "Test pype patch",
                   }
    implemented_by_PR = "666"

    """ Test implementation of patch """
    def __init__(self, avalon_connection=None, pype_connection=None):
        log.debug("init TestPatch")

        self.avalon_conn = avalon_connection
        self.pype_conn = pype_connection

    def update_avalon_global(self):
        log.debug("TestPatch.update_avalon_global")
        try:
            for project_name in self.avalon_conn.projects():
                log.debug("project_name:: {}".format(project_name['name']))
                raise ValueError("temp")
        except Exception as exp:
            log.warning(
                "Error has happened during update_avalon_project",
                exc_info=True
            )
            return False, str(exp)

        return True, ''

    def update_avalon_project(self, project_name):
        log.debug("TestPatch.update_avalon_project {}".format(project_name))
        filter = {"name": "test_object"}
        update_object = {"$set": {"name": "test_object_upd"}}
        try:
            self.avalon_conn.Session["AVALON_PROJECT"] = project_name
            self.avalon_conn.update_one(filter, update_object)
        except Exception as exp:
            log.warning(
                "Error has happened during update_avalon_project",
                exc_info=True
            )
            return False, str(exp)

        return True, ''

    def update_api(self, api):
        log.debug("TestPatch.update_avalon_global")
        return True

    def update_pype_db(self):
        log.debug("TestPatch.update_pype_db")
        new_object = {"name": "test_object"}

        try:
            self.pype_conn.database.upgrade_patches.insert_one(new_object)
        except Exception as exp:
            log.warning(
                "Error has happened during update_pype_db",
                exc_info=True
            )
            return False, str(exp)

        return True, ''

    def run(self, projects=[]):
        log.debug("run TestPatch")
        result, error = self.update_avalon_global()
        if result:
            for project_name in projects:
                result, error = self.update_avalon_project(project_name)
                if not result:
                    break
        if result:
            result, error = self.update_pype_db()

        return result, error
