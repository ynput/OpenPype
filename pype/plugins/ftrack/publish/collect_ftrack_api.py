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
        self.log.debug("Ftrack user: \"{0}\"".format(session.api_user))
        context.data["ftrackSession"] = session

        # Collect task

        project_name = os.environ.get('AVALON_PROJECT', '')
        asset_name = os.environ.get('AVALON_ASSET', '')
        task_name = os.environ.get('AVALON_TASK', None)

        # Find project entity
        project_query = 'Project where full_name is "{0}"'.format(project_name)
        self.log.debug("Project query: < {0} >".format(project_query))
        project_entity = session.query(project_query).one()
        self.log.debug("Project found: {0}".format(project_entity))

        # Find asset entity
        entity_query = (
            'TypedContext where project_id is "{0}"'
            ' and name is "{1}"'
        ).format(project_entity["id"], asset_name)
        self.log.debug("Asset entity query: < {0} >".format(entity_query))
        asset_entity = session.query(entity_query).one()
        self.log.debug("Asset found: {0}".format(asset_entity))

        # Find task entity if task is set
        if task_name:
            task_query = (
                'Task where name is "{0}" and parent_id is "{1}"'
            ).format(task_name, asset_entity["id"])
            self.log.debug("Task entity query: < {0} >".format(task_query))
            task_entity = session.query(task_query).one()
            self.log.debug("Task entity found: {0}".format(task_entity))

        else:
            task_entity = None
            self.log.warning("Task name is not set.")

        context.data["ftrackProject"] = asset_entity
        context.data["ftrackEntity"] = asset_entity
        context.data["ftrackTask"] = task_entity
