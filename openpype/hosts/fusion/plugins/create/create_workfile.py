import collections

import qtawesome

import openpype.hosts.fusion.api as api
from openpype.client import get_asset_by_name
from openpype.pipeline import (
    AutoCreator,
    CreatedInstance,
    legacy_io,
)


def flatten_dict(d, parent_key=None, separator="."):
    items = []
    for key, v in d.items():
        new_key = parent_key + separator + key if parent_key else key
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten_dict(v, new_key, separator=separator).items())
        else:
            items.append((new_key, v))
    return dict(items)


class FusionWorkfileCreator(AutoCreator):
    identifier = "workfile"
    family = "workfile"
    label = "Workfile"

    default_variant = "Main"

    create_allow_context_change = False

    data_key = "openpype.workfile"

    def collect_instances(self):

        comp = api.get_current_comp()
        data = comp.GetData(self.data_key)
        if not data:
            return

        instance = CreatedInstance(
            family=self.family,
            subset_name=data["subset"],
            data=data,
            creator=self
        )
        instance.transient_data["comp"] = comp
        instance.transient_data["tool"] = None

        self._add_instance_to_context(instance)

    def update_instances(self, update_list):
        for update in update_list:
            instance = update.instance
            comp = instance.transient_data["comp"]
            if not hasattr(comp, "SetData"):
                # Comp is not alive anymore, likely closed by the user
                self.log.error("Workfile comp not found for existing instance."
                               " Comp might have been closed in the meantime.")
                continue

            # TODO: It appears sometimes this could be 'nested'
            # Get the new values after the changes by key, ignore old value
            new_data = {
                key: new for key, (_old, new) in update.changes.items()
            }
            self._imprint(comp, new_data)

    def create(self, options=None):

        comp = api.get_current_comp()
        if not comp:
            self.log.error("Unable to find current comp")
            return

        # TODO: Is this really necessary?
        # Force kill any existing "workfile" instances
        for instance in self.create_context.instances:
            if instance.family == self.family:
                self.log.debug(f"Removing instance: {instance}")
                self._remove_instance_from_context(instance)

        project_name = legacy_io.Session["AVALON_PROJECT"]
        asset_name = legacy_io.Session["AVALON_ASSET"]
        task_name = legacy_io.Session["AVALON_TASK"]
        host_name = legacy_io.Session["AVALON_APP"]

        asset_doc = get_asset_by_name(project_name, asset_name)
        subset_name = self.get_subset_name(
            self.default_variant, task_name, asset_doc,
            project_name, host_name
        )
        data = {
            "asset": asset_name,
            "task": task_name,
            "variant": self.default_variant
        }
        data.update(self.get_dynamic_data(
            self.default_variant, task_name, asset_doc,
            project_name, host_name
        ))

        instance = CreatedInstance(
            self.family, subset_name, data, self
        )
        instance.transient_data["comp"] = comp
        instance.transient_data["tool"] = None
        self._add_instance_to_context(instance)

        self._imprint(comp, data)

    def get_icon(self):
        return qtawesome.icon("fa.file-o", color="white")

    def _imprint(self, comp, data):

        # TODO: Should this keys persist or not? I'd prefer not
        # Do not persist the current context for the Workfile
        for key in ["variant", "subset", "asset", "task"]:
            data.pop(key, None)

        # Flatten any potential nested dicts
        data = flatten_dict(data, separator=".")

        # Prefix with data key openpype.workfile
        data = {f"{self.data_key}.{key}" for key, value in data.items()}
        comp.SetData(data)
