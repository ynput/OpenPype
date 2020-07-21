import sys
import pyblish.api
import avalon.api

try:
    from pype.modules.ftrack.lib.avalon_sync import CUST_ATTR_AUTO_SYNC
except Exception:
    CUST_ATTR_AUTO_SYNC = "avalon_auto_sync"


class IntegrateAutoSyncBackOn(pyblish.api.ContextPlugin):
    """Ensure that autosync value in ftrack project is set to True.

    In case was set to False and event server with the sync to avalon event
    is not running this will set synchronization back on.
    """

    order = pyblish.api.IntegratorOrder + 1
    families = ['clip']
    label = 'Ftrack project\'s auto sync on'

    def process(self, context):
        session = context.data["ftrackSession"]
        project_name = avalon.api.Session["AVALON_PROJECT"]
        query = 'Project where full_name is "{}"'.format(project_name)
        project = session.query(query).one()
        if not project["custom_attributes"][CUST_ATTR_AUTO_SYNC]:
            project["custom_attributes"][CUST_ATTR_AUTO_SYNC] = True

        try:
            session.commit()
        except Exception:
            tp, value, tb = sys.exc_info()
            session.rollback()
            raise
