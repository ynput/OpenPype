import pyblish.api
from openpype.lib import filter_profiles


class IntegrateFtrackFarmStatus(pyblish.api.ContextPlugin):
    """Change task status when should be published on farm.

    Instance which has set "farm" key in data to 'True' is considered as will
    be rendered on farm thus it's status should be changed.
    """

    order = pyblish.api.IntegratorOrder + 0.48
    label = "Integrate Ftrack Farm Status"

    farm_status_profiles = []

    def process(self, context):
        # Quick end
        if not self.farm_status_profiles:
            project_name = context.data["projectName"]
            self.log.info((
                "Status profiles are not filled for project \"{}\". Skipping"
            ).format(project_name))
            return

        filtered_instances = self.filter_instances(context)
        instances_with_status_names = self.get_instances_with_statuse_names(
            context, filtered_instances
        )
        if instances_with_status_names:
            self.fill_statuses(context, instances_with_status_names)

    def filter_instances(self, context):
        filtered_instances = []
        for instance in context:
            # Skip disabled instances
            if instance.data.get("publish") is False:
                continue
            subset_name = instance.data["subset"]
            msg_start = "Skipping instance {}.".format(subset_name)
            if not instance.data.get("farm"):
                self.log.debug(
                    "{} Won't be rendered on farm.".format(msg_start)
                )
                continue

            task_entity = instance.data.get("ftrackTask")
            if not task_entity:
                self.log.debug(
                    "{} Does not have filled task".format(msg_start)
                )
                continue

            filtered_instances.append(instance)
        return filtered_instances

    def get_instances_with_statuse_names(self, context, instances):
        instances_with_status_names = []
        for instance in instances:
            family = instance.data["family"]
            subset_name = instance.data["subset"]
            task_entity = instance.data["ftrackTask"]
            host_name = context.data["hostName"]
            task_name = task_entity["name"]
            task_type = task_entity["type"]["name"]
            status_profile = filter_profiles(
                self.farm_status_profiles,
                {
                    "hosts": host_name,
                    "task_types": task_type,
                    "task_names": task_name,
                    "families": family,
                    "subsets": subset_name,
                },
                logger=self.log
            )
            if not status_profile:
                # There already is log in 'filter_profiles'
                continue

            status_name = status_profile["status_name"]
            if status_name:
                instances_with_status_names.append((instance, status_name))
        return instances_with_status_names

    def fill_statuses(self, context, instances_with_status_names):
        # Prepare available task statuses on the project
        project_name = context.data["projectName"]
        session = context.data["ftrackSession"]
        project_entity = session.query((
            "select project_schema from Project where full_name is \"{}\""
        ).format(project_name)).one()
        project_schema = project_entity["project_schema"]

        task_type_ids = set()
        for item in instances_with_status_names:
            instance, _ = item
            task_entity = instance.data["ftrackTask"]
            task_type_ids.add(task_entity["type"]["id"])

        task_statuses_by_type_id = {
            task_type_id: project_schema.get_statuses("Task", task_type_id)
            for task_type_id in task_type_ids
        }

        # Keep track if anything has changed
        skipped_status_names = set()
        status_changed = False
        for item in instances_with_status_names:
            instance, status_name = item
            task_entity = instance.data["ftrackTask"]
            task_statuses = task_statuses_by_type_id[task_entity["type"]["id"]]
            status_name_low = status_name.lower()

            status_id = None
            # Skip if status name was already tried to be found
            for status in task_statuses:
                if status["name"].lower() == status_name_low:
                    status_id = status["id"]
                    break

            if status_id is None:
                if status_name_low not in skipped_status_names:
                    skipped_status_names.add(status_name_low)
                    joined_status_names = ", ".join({
                        '"{}"'.format(status["name"])
                        for status in task_statuses
                    })
                    self.log.warning((
                        "Status \"{}\" is not available on project \"{}\"."
                        " Available statuses are {}"
                    ).format(status_name, project_name, joined_status_names))
                continue

            # Change task status id
            if status_id != task_entity["status_id"]:
                task_entity["status_id"] = status_id
                status_changed = True

        if status_changed:
            session.commit()
