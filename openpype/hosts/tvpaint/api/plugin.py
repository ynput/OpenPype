import re

from openpype.pipeline import LoaderPlugin
from openpype.pipeline.create import (
    CreatedInstance,
    get_subset_name,
    AutoCreator,
    Creator,
)
from openpype.pipeline.create.creator_plugins import cache_and_get_instances

from .lib import get_layers_data


SHARED_DATA_KEY = "openpype.tvpaint.instances"


class TVPaintCreatorCommon:
    @property
    def subset_template_family_filter(self):
        return self.family

    def _cache_and_get_instances(self):
        return cache_and_get_instances(
            self, SHARED_DATA_KEY, self.host.list_instances
        )

    def _collect_create_instances(self):
        instances_by_identifier = self._cache_and_get_instances()
        for instance_data in instances_by_identifier[self.identifier]:
            instance = CreatedInstance.from_existing(instance_data, self)
            self._add_instance_to_context(instance)

    def _update_create_instances(self, update_list):
        if not update_list:
            return

        cur_instances = self.host.list_instances()
        cur_instances_by_id = {}
        for instance_data in cur_instances:
            instance_id = instance_data.get("instance_id")
            if instance_id:
                cur_instances_by_id[instance_id] = instance_data

        for instance, changes in update_list:
            instance_data = changes.new_value
            cur_instance_data = cur_instances_by_id.get(instance.id)
            if cur_instance_data is None:
                cur_instances.append(instance_data)
                continue
            for key in set(cur_instance_data) - set(instance_data):
                cur_instance_data.pop(key)
            cur_instance_data.update(instance_data)
        self.host.write_instances(cur_instances)

    def _custom_get_subset_name(
        self,
        variant,
        task_name,
        asset_doc,
        project_name,
        host_name=None,
        instance=None
    ):
        dynamic_data = self.get_dynamic_data(
            variant, task_name, asset_doc, project_name, host_name, instance
        )

        return get_subset_name(
            self.family,
            variant,
            task_name,
            asset_doc,
            project_name,
            host_name,
            dynamic_data=dynamic_data,
            project_settings=self.project_settings,
            family_filter=self.subset_template_family_filter
        )


class TVPaintCreator(Creator, TVPaintCreatorCommon):
    def collect_instances(self):
        self._collect_create_instances()

    def update_instances(self, update_list):
        self._update_create_instances(update_list)

    def remove_instances(self, instances):
        ids_to_remove = {
            instance.id
            for instance in instances
        }
        cur_instances = self.host.list_instances()
        changed = False
        new_instances = []
        for instance_data in cur_instances:
            if instance_data.get("instance_id") in ids_to_remove:
                changed = True
            else:
                new_instances.append(instance_data)

        if changed:
            self.host.write_instances(new_instances)

        for instance in instances:
            self._remove_instance_from_context(instance)

    def get_dynamic_data(self, *args, **kwargs):
        # Change asset and name by current workfile context
        create_context = self.create_context
        asset_name = create_context.get_current_asset_name()
        task_name = create_context.get_current_task_name()
        output = {}
        if asset_name:
            output["asset"] = asset_name
            if task_name:
                output["task"] = task_name
        return output

    def get_subset_name(self, *args, **kwargs):
        return self._custom_get_subset_name(*args, **kwargs)

    def _store_new_instance(self, new_instance):
        instances_data = self.host.list_instances()
        instances_data.append(new_instance.data_to_store())
        self.host.write_instances(instances_data)
        self._add_instance_to_context(new_instance)


class TVPaintAutoCreator(AutoCreator, TVPaintCreatorCommon):
    def collect_instances(self):
        self._collect_create_instances()

    def update_instances(self, update_list):
        self._update_create_instances(update_list)

    def get_subset_name(self, *args, **kwargs):
        return self._custom_get_subset_name(*args, **kwargs)


class Loader(LoaderPlugin):
    hosts = ["tvpaint"]

    @staticmethod
    def get_members_from_container(container):
        if "members" not in container and "objectName" in container:
            # Backwards compatibility
            layer_ids_str = container.get("objectName")
            return [
                int(layer_id) for layer_id in layer_ids_str.split("|")
            ]
        return container["members"]

    def get_unique_layer_name(self, asset_name, name):
        """Layer name with counter as suffix.

        Find higher 3 digit suffix from all layer names in scene matching regex
        `{asset_name}_{name}_{suffix}`. Higher 3 digit suffix is used
        as base for next number if scene does not contain layer matching regex
        `0` is used ase base.

        Args:
            asset_name (str): Name of subset's parent asset document.
            name (str): Name of loaded subset.

        Returns:
            (str): `{asset_name}_{name}_{higher suffix + 1}`
        """
        layer_name_base = "{}_{}".format(asset_name, name)

        counter_regex = re.compile(r"_(\d{3})$")

        higher_counter = 0
        for layer in get_layers_data():
            layer_name = layer["name"]
            if not layer_name.startswith(layer_name_base):
                continue
            number_subpart = layer_name[len(layer_name_base):]
            groups = counter_regex.findall(number_subpart)
            if len(groups) != 1:
                continue

            counter = int(groups[0])
            if counter > higher_counter:
                higher_counter = counter
                continue

        return "{}_{:0>3d}".format(layer_name_base, higher_counter + 1)
