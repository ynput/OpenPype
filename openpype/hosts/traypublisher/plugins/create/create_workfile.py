from openpype.hosts.traypublisher.api import pipeline
from openpype.lib import FileDef
from openpype.pipeline import (
    Creator,
    CreatedInstance
)


class WorkfileCreator(Creator):
    identifier = "workfile"
    label = "Workfile"
    family = "workfile"
    description = "Publish backup of workfile"

    create_allow_context_change = True

    extensions = [
        # Maya
        ".ma", ".mb",
        # Nuke
        ".nk",
        # Hiero
        ".hrox",
        # Houdini
        ".hip", ".hiplc", ".hipnc",
        # Blender
        ".blend",
        # Celaction
        ".scn",
        # TVPaint
        ".tvpp",
        # Fusion
        ".comp",
        # Harmony
        ".zip",
        # Premiere
        ".prproj",
        # Resolve
        ".drp",
        # Photoshop
        ".psd", ".psb",
        # Aftereffects
        ".aep"
    ]

    def get_icon(self):
        return "fa.file"

    def collect_instances(self):
        for instance_data in pipeline.list_instances():
            creator_id = instance_data.get("creator_identifier")
            if creator_id == self.identifier:
                instance = CreatedInstance.from_existing(
                    instance_data, self
                )
                self._add_instance_to_context(instance)

    def update_instances(self, update_list):
        pipeline.update_instances(update_list)

    def remove_instances(self, instances):
        pipeline.remove_instances(instances)
        for instance in instances:
            self._remove_instance_from_context(instance)

    def create(self, subset_name, data, pre_create_data):
        # Pass precreate data to creator attributes
        data["creator_attributes"] = pre_create_data
        # Create new instance
        new_instance = CreatedInstance(self.family, subset_name, data, self)
        # Host implementation of storing metadata about instance
        pipeline.HostContext.add_instance(new_instance.data_to_store())
        # Add instance to current context
        self._add_instance_to_context(new_instance)

    def get_default_variants(self):
        return [
            "Main"
        ]

    def get_instance_attr_defs(self):
        output = [
            FileDef(
                "filepath",
                folders=False,
                extensions=self.extensions,
                label="Filepath"
            )
        ]
        return output

    def get_pre_create_attr_defs(self):
        # Use same attributes as for instance attrobites
        return self.get_instance_attr_defs()

    def get_detail_description(self):
        return """# Publish workfile backup"""
