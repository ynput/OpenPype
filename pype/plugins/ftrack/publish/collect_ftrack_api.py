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
        session = ftrack_api.Session(auto_connect_event_hub=True)
        self.log.debug("Ftrack user: \"{0}\"".format(session.api_user))
        context.data["ftrackSession"] = session

        # Collect task

        project_name = os.environ.get('AVALON_PROJECT', '')
        asset_name = os.environ.get('AVALON_ASSET', '')
        task_name = os.environ.get('AVALON_TASK', None)

        # Find project entity
        project_query = 'Project where full_name is "{0}"'.format(project_name)
        self.log.debug("Project query: < {0} >".format(project_query))
        project_entity = list(session.query(project_query).all())
        if len(project_entity) == 0:
            raise AssertionError(
                "Project \"{0}\" not found in Ftrack.".format(project_name)
            )
        # QUESTION Is possible to happen?
        elif len(project_entity) > 1:
            raise AssertionError((
                "Found more than one project with name \"{0}\" in Ftrack."
            ).format(project_name))

        project_entity = project_entity[0]
        self.log.debug("Project found: {0}".format(project_entity))

        # Find asset entity
        entity_query = (
            'TypedContext where project_id is "{0}"'
            ' and name is "{1}"'
        ).format(project_entity["id"], asset_name)
        self.log.debug("Asset entity query: < {0} >".format(entity_query))
        asset_entities = []
        for entity in session.query(entity_query).all():
            # Skip tasks
            if entity.entity_type.lower() != "task":
                asset_entities.append(entity)

        if len(asset_entities) == 0:
            raise AssertionError((
                "Entity with name \"{0}\" not found"
                " in Ftrack project \"{1}\"."
            ).format(asset_name, project_name))

        elif len(asset_entities) > 1:
            raise AssertionError((
                "Found more than one entity with name \"{0}\""
                " in Ftrack project \"{1}\"."
            ).format(asset_name, project_name))

        asset_entity = asset_entities[0]
        self.log.debug("Asset found: {0}".format(asset_entity))

        # Find task entity if task is set
        if task_name:
            task_query = (
                'Task where name is "{0}" and parent_id is "{1}"'
            ).format(task_name, asset_entity["id"])
            self.log.debug("Task entity query: < {0} >".format(task_query))
            task_entity = session.query(task_query).first()
            if not task_entity:
                self.log.warning(
                    "Task entity with name \"{0}\" was not found.".format(
                        task_name
                    )
                )
            else:
                self.log.debug("Task entity found: {0}".format(task_entity))

        else:
            task_entity = None
            self.log.warning("Task name is not set.")

        context.data["ftrackProject"] = project_entity
        context.data["ftrackEntity"] = asset_entity
        context.data["ftrackTask"] = task_entity
