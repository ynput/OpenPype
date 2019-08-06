import os
import pyblish.api
import logging

try:
    import ftrack_api_old as ftrack_api
except Exception:
    import ftrack_api


class CollectFtrackApi(pyblish.api.ContextPlugin):
    """ Collects an ftrack session and the current task id. """

    order = pyblish.api.CollectorOrder
    label = "Collect Ftrack Api"

    def process(self, context):

        ftrack_log = logging.getLogger('ftrack_api')
        ftrack_log.setLevel(logging.WARNING)
        ftrack_log = logging.getLogger('ftrack_api_old')
        ftrack_log.setLevel(logging.WARNING)

        # Collect session
        session = ftrack_api.Session()
        context.data["ftrackSession"] = session

        # Collect task

        project = os.environ.get('AVALON_PROJECT', '')
        asset = os.environ.get('AVALON_ASSET', '')
        task = os.environ.get('AVALON_TASK', None)
        self.log.debug(task)

        if task:
            result = session.query('Task where\
                project.full_name is "{0}" and\
                name is "{1}" and\
                parent.name is "{2}"'.format(project, task, asset)).one()
            context.data["ftrackTask"] = result
        else:
            result = session.query('TypedContext where\
                project.full_name is "{0}" and\
                name is "{1}"'.format(project, asset)).one()
            context.data["ftrackEntity"] = result

        self.log.info(result)
