import sys
import pyblish.api
import pype.api
import avalon.api

try:
    from pype.modules.ftrack.lib.avalon_sync import CUST_ATTR_AUTO_SYNC
except Exception:
    CUST_ATTR_AUTO_SYNC = "avalon_auto_sync"


class ValidateAutoSyncOff(pyblish.api.ContextPlugin):
    """Ensure that autosync value in ftrack project is set to False.

    In case was set to True and event server with the sync to avalon event
    is running will cause integration to avalon will be override.

    """

    order = pyblish.api.ValidatorOrder
    families = ['clip']
    label = 'Ftrack project\'s auto sync off'
    actions = [pype.api.RepairAction]

    def process(self, context):
        invalid = self.get_invalid(context)
        assert not invalid, (
            "Ftrack Project has 'Auto sync' set to On."
            " That may cause issues during integration."
        )

    @staticmethod
    def get_invalid(context):
        session = context.data["ftrackSession"]
        project_name = avalon.api.Session["AVALON_PROJECT"]
        query = 'Project where full_name is "{}"'.format(project_name)
        project = session.query(query).one()
        if project["custom_attributes"][CUST_ATTR_AUTO_SYNC]:
            return project

    @classmethod
    def repair(cls, context):
        session = context.data["ftrackSession"]
        invalid = cls.get_invalid(context)
        invalid["custom_attributes"][CUST_ATTR_AUTO_SYNC] = False
        try:
            session.commit()
        except Exception:
            tp, value, tb = sys.exc_info()
            session.rollback()
            raise
