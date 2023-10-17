import logging
import pyblish.api


class CollectFtrackApi(pyblish.api.ContextPlugin):
    """ Collects an ftrack session and the current task id. """

    order = pyblish.api.CollectorOrder + 0.4991
    label = "Collect Ftrack Api"

    def process(self, context):
        ftrack_log = logging.getLogger('ftrack_api')
        ftrack_log.setLevel(logging.WARNING)
        ftrack_log = logging.getLogger('ftrack_api_old')
        ftrack_log.setLevel(logging.WARNING)

        # Collect session
        # NOTE Import python module here to know if import was successful
        import ftrack_api

        session = ftrack_api.Session(auto_connect_event_hub=False)
        self.log.debug("Ftrack user: \"{0}\"".format(session.api_user))

        # Collect task
        project_name = context.data["projectName"]
        asset_name = context.data["asset"]
        task_name = context.data["task"]

        # Find project entity
        project_query = 'Project where full_name is "{0}"'.format(project_name)
        self.log.debug("Project query: < {0} >".format(project_query))
        project_entities = list(session.query(project_query).all())
        if len(project_entities) == 0:
            raise AssertionError(
                "Project \"{0}\" not found in Ftrack.".format(project_name)
            )
        # QUESTION Is possible to happen?
        elif len(project_entities) > 1:
            raise AssertionError((
                "Found more than one project with name \"{0}\" in Ftrack."
            ).format(project_name))

        project_entity = project_entities[0]

        self.log.debug("Project found: {0}".format(project_entity))

        task_object_type = session.query(
            "ObjectType where name is 'Task'").one()
        task_object_type_id = task_object_type["id"]
        asset_entity = None
        if asset_name:
            # Find asset entity
            entity_query = (
                "TypedContext where project_id is '{}'"
                " and name is '{}'"
                " and object_type_id != '{}'"
            ).format(
                project_entity["id"],
                asset_name,
                task_object_type_id
            )
            self.log.debug("Asset entity query: < {0} >".format(entity_query))
            asset_entities = []
            for entity in session.query(entity_query).all():
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

        task_entity = None
        # Find task entity if task is set
        if not asset_entity:
            self.log.warning(
                "Asset entity is not set. Skipping query of task entity."
            )
        elif not task_name:
            self.log.warning("Task name is not set.")
        else:
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

        context.data["ftrackSession"] = session
        context.data["ftrackPythonModule"] = ftrack_api
        context.data["ftrackProject"] = project_entity
        context.data["ftrackEntity"] = asset_entity
        context.data["ftrackTask"] = task_entity

        self.per_instance_process(
            context,
            asset_entity,
            task_entity,
            task_object_type_id
        )

    def per_instance_process(
        self,
        context,
        context_asset_entity,
        context_task_entity,
        task_object_type_id
    ):
        context_task_name = None
        context_asset_name = None
        if context_asset_entity:
            context_asset_name = context_asset_entity["name"]
            if context_task_entity:
                context_task_name = context_task_entity["name"]
        instance_by_asset_and_task = {}
        for instance in context:
            self.log.debug(
                "Checking entities of instance \"{}\"".format(str(instance))
            )
            instance_asset_name = instance.data.get("asset")
            instance_task_name = instance.data.get("task")

            if not instance_asset_name and not instance_task_name:
                self.log.debug("Instance does not have set context keys.")
                instance.data["ftrackEntity"] = context_asset_entity
                instance.data["ftrackTask"] = context_task_entity
                continue

            elif instance_asset_name and instance_task_name:
                if (
                    instance_asset_name == context_asset_name
                    and instance_task_name == context_task_name
                ):
                    self.log.debug((
                        "Instance's context is same as in publish context."
                        " Asset: {} | Task: {}"
                    ).format(context_asset_name, context_task_name))
                    instance.data["ftrackEntity"] = context_asset_entity
                    instance.data["ftrackTask"] = context_task_entity
                    continue
                asset_name = instance_asset_name
                task_name = instance_task_name

            elif instance_task_name:
                if instance_task_name == context_task_name:
                    self.log.debug((
                        "Instance's context task is same as in publish"
                        " context. Task: {}"
                    ).format(context_task_name))
                    instance.data["ftrackEntity"] = context_asset_entity
                    instance.data["ftrackTask"] = context_task_entity
                    continue

                asset_name = context_asset_name
                task_name = instance_task_name

            elif instance_asset_name:
                if instance_asset_name == context_asset_name:
                    self.log.debug((
                        "Instance's context asset is same as in publish"
                        " context. Asset: {}"
                    ).format(context_asset_name))
                    instance.data["ftrackEntity"] = context_asset_entity
                    instance.data["ftrackTask"] = context_task_entity
                    continue

                # Do not use context's task name
                task_name = instance_task_name
                asset_name = instance_asset_name

            if asset_name not in instance_by_asset_and_task:
                instance_by_asset_and_task[asset_name] = {}

            if task_name not in instance_by_asset_and_task[asset_name]:
                instance_by_asset_and_task[asset_name][task_name] = []
            instance_by_asset_and_task[asset_name][task_name].append(instance)

        if not instance_by_asset_and_task:
            return

        session = context.data["ftrackSession"]
        project_entity = context.data["ftrackProject"]
        asset_names = set(instance_by_asset_and_task.keys())

        joined_asset_names = ",".join([
            "\"{}\"".format(name)
            for name in asset_names
        ])
        entities = session.query(
            (
                "TypedContext where project_id is \"{}\" and name in ({})"
                " and object_type_id != '{}'"
            ).format(
                project_entity["id"],
                joined_asset_names,
                task_object_type_id
            )
        ).all()

        entities_by_name = {
            entity["name"]: entity
            for entity in entities
        }
        for asset_name, by_task_data in instance_by_asset_and_task.items():
            entity = entities_by_name.get(asset_name)
            task_entity_by_name = {}
            if not entity:
                self.log.warning((
                    "Didn't find entity with name \"{}\" in Project \"{}\""
                ).format(asset_name, project_entity["full_name"]))
            else:
                task_entities = session.query((
                    "select id, name from Task where parent_id is \"{}\""
                ).format(entity["id"])).all()
                for task_entity in task_entities:
                    task_name_low = task_entity["name"].lower()
                    task_entity_by_name[task_name_low] = task_entity

            for task_name, instances in by_task_data.items():
                task_entity = None
                if task_name and entity:
                    task_entity = task_entity_by_name.get(task_name.lower())

                for instance in instances:
                    instance.data["ftrackEntity"] = entity
                    instance.data["ftrackTask"] = task_entity

                    self.log.debug((
                        "Instance {} has own ftrack entities"
                        " as has different context. TypedContext: {} Task: {}"
                    ).format(str(instance), str(entity), str(task_entity)))
