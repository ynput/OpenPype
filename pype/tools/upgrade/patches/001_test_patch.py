from pype.tools.upgrade.patches.abtract_patch import AbstractPatch
from pype.api import Logger

log = Logger().get_logger("UpgradeExecutor")


class TestPatch(AbstractPatch):
    """
        Example implementation of Patch.
        It requires working connection (avalon_connections for changes in
        avalon DB, pype_connection for pype DB and Settings)

        It implements most available methods from AbstractPatch in basic way.
        Real world Patch could reimplemented anything needed, set pass to
        any unwanted abstract methods.
    """
    # implemented this way to reuse properties from AbstractPatch
    name = '001_test_patch'  # should follow name of file
    version = "1.0.0"
    affects = ["global", "project", "pype_db"]
    applied_on = {}
    description = {"global": "Test global db patch",
                   "project": "Test project based updates",
                   "pype_db": "Test pype patch",
                   }
    implemented_by_PR = "666"

    """ Test implementation of patch """
    def __init__(self, avalon_connection=None, pype_connection=None):
        log.debug("TestPatch.init")

        self.avalon_conn = avalon_connection
        self.pype_conn = pype_connection

    def run_global(self):
        log.debug("TestPatch.run_global")
        result, error = super().run_global()

        return result, error

    def run_on_project(self, project_name):
        log.debug("TestPatch.run_on_project")
        result, error = super().run_on_project(project_name)

        return result, error

    def update_avalon_global(self):
        log.debug("TestPatch.update_avalon_global")
        try:
            log.debug("run something not project dependent")
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

    def update_api(self, api=None):
        log.debug("TestPatch.update_api")
        return True, ''

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

    # not used methods - take only skeleton functionality
    def update_settings_global(self):
        super().update_settings_global()

    def update_settings_project(self, project_name):
        super().update_settings_project()
