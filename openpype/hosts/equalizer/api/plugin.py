"""Base plugin class for 3DEqualizer.

note:
    3dequalizer 7.1v2 uses Python 3.7.9

"""
from abc import ABC
from typing import Dict, List
from openpype.hosts.equalizer.api import EqualizerHost
from openpype.pipeline import CreatedInstance, Creator, CreatorError


class EqualizerCreator(ABC, Creator):

    @property
    def host(self) -> EqualizerHost:
        """Return the host application."""
        # We need to cast the host to EqualizerHost, because the Creator
        # class is not aware of the host application.
        return super().host

    def collect_instances(self):
        """Collect instances from the host application.

        Returns:
            list[openpype.pipeline.CreatedInstance]: List of instances.
        """
        return self.host.get_context_data().get("publish_instances", [])

    def update_instances(self, update_list):
        if not update_list:
            return
        context = self.host.get_context_data()

        if not context.get("publish_instances"):
            context["publish_instances"] = []

        instances_by_id = {}
        for instance in context.get("publish_instances"):
            # sourcery skip: use-named-expression
            instance_id = instance.get("instance_id")
            if instance_id:
                instances_by_id[instance_id] = instance

        for instance, changes in update_list:
            new_instance_data = changes.new_value
            instance_data = instances_by_id.get(instance.id)
            # instance doesn't exist, append everything
            if instance_data is None:
                context["publish_instances"].append(new_instance_data)
                continue

            # update only changed values on instance
            for key in set(instance_data) - set(new_instance_data):
                instance_data.pop(key)
                instance_data.update(new_instance_data)

        self.host.update_context_data(context, changes=update_list)

    def remove_instances(self, instances: List[Dict]):
        context = self.host.get_context_data()
        if not context.get("publish_instances"):
            context["publish_instances"] = []

        ids_to_remove = [
            instance.get("instance_id")
            for instance in instances
        ]
        for instance in context.get("publish_instances"):
            if instance.get("instance_id") in ids_to_remove:
                context["publish_instances"].remove(instance)

        self.host.update_context_data(context, changes={})
