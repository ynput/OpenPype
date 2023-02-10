"""Render Layer and Passes creators.

Render layer is main part which is represented by group in TVPaint. All TVPaint
layers marked with that group color are part of the render layer. To be more
specific about some parts of layer it is possible to create sub-sets of layer
which are named passes. Render pass consist of layers in same color group as
render layer but define more specific part.

For example render layer could be 'Bob' which consist of 5 TVPaint layers.
- Bob has 'head' which consist of 2 TVPaint layers -> Render pass 'head'
- Bob has 'body' which consist of 1 TVPaint layer -> Render pass 'body'
- Bob has 'arm' which consist of 1 TVPaint layer -> Render pass 'arm'
- Last layer does not belong to render pass at all

Bob will be rendered as 'beauty' of bob (all visible layers in group).
His head will be rendered too but without any other parts. The same for body
and arm.

What is this good for? Compositing has more power how the renders are used.
Can do transforms on each render pass without need to modify a re-render them
using TVPaint.

The workflow may hit issues when there are used other blending modes than
default 'color' blend more. In that case it is not recommended to use this
workflow at all as other blend modes may affect all layers in clip which can't
be done.

Todos:
    Add option to extract marked layers and passes as json output format for
        AfterEffects.
"""

import collections

from openpype.lib import (
    prepare_template_data,
    EnumDef,
    TextDef,
    BoolDef,
)
from openpype.pipeline.create import (
    CreatedInstance,
    CreatorError,
)
from openpype.hosts.tvpaint.api.plugin import TVPaintCreator
from openpype.hosts.tvpaint.api.lib import (
    get_layers_data,
    get_groups_data,
    execute_george_through_file,
)


class CreateRenderlayer(TVPaintCreator):
    """Mark layer group as one instance."""

    label = "Render Layer"
    family = "render"
    subset_template_family_filter = "renderLayer"
    identifier = "render.layer"
    icon = "fa.cube"

    # George script to change color group
    rename_script_template = (
        "tv_layercolor \"setcolor\""
        " {clip_id} {group_id} {r} {g} {b} \"{name}\""
    )
    order = 90

    # Settings
    render_pass = "beauty"
    mark_for_review = True

    def get_dynamic_data(
        self, variant, task_name, asset_doc, project_name, host_name, instance
    ):
        dynamic_data = super().get_dynamic_data(
            variant, task_name, asset_doc, project_name, host_name, instance
        )
        dynamic_data["renderpass"] = self.render_pass
        dynamic_data["renderlayer"] = variant
        return dynamic_data

    def _get_selected_group_ids(self):
        return {
            layer["group_id"]
            for layer in get_layers_data()
            if layer["selected"]
        }

    def create(self, subset_name, instance_data, pre_create_data):
        self.log.debug("Query data from workfile.")

        group_id = pre_create_data.get("group_id")
        # This creator should run only on one group
        if group_id is None or group_id == -1:
            selected_groups = self._get_selected_group_ids()
            selected_groups.discard(0)
            if len(selected_groups) > 1:
                raise CreatorError("You have selected more than one group")

            if len(selected_groups) == 0:
                raise CreatorError("You don't have selected any group")
            group_id = tuple(selected_groups)[0]

        self.log.debug("Querying groups data from workfile.")
        groups_data = get_groups_data()
        group_item = None
        for group_data in groups_data:
            if group_data["group_id"] == group_id:
                group_item = group_data

        for instance in self.create_context.instances:
            if (
                instance.creator_identifier == self.identifier
                and instance["creator_attributes"]["group_id"] == group_id
            ):
                raise CreatorError((
                    f"Group \"{group_item.get('name')}\" is already used"
                    f" by another render layer \"{instance['subset']}\""
                ))

        self.log.debug(f"Selected group id is \"{group_id}\".")
        if "creator_attributes" not in instance_data:
            instance_data["creator_attributes"] = {}
        creator_attributes = instance_data["creator_attributes"]
        mark_for_review = pre_create_data.get("mark_for_review")
        if mark_for_review is None:
            mark_for_review = self.mark_for_review
        creator_attributes["group_id"] = group_id
        creator_attributes["mark_for_review"] = mark_for_review

        self.log.info(f"Subset name is {subset_name}")
        new_instance = CreatedInstance(
            self.family,
            subset_name,
            instance_data,
            self
        )
        self._store_new_instance(new_instance)

        new_group_name = pre_create_data.get("group_name")
        if not new_group_name or not group_id:
            return

        self.log.debug("Changing name of the group.")

        new_group_name = pre_create_data.get("group_name")
        if not new_group_name or group_item["name"] == new_group_name:
            return
        # Rename TVPaint group (keep color same)
        # - groups can't contain spaces
        rename_script = self.rename_script_template.format(
            clip_id=group_item["clip_id"],
            group_id=group_item["group_id"],
            r=group_item["red"],
            g=group_item["green"],
            b=group_item["blue"],
            name=new_group_name
        )
        execute_george_through_file(rename_script)

        self.log.info((
            f"Name of group with index {group_id}"
            f" was changed to \"{new_group_name}\"."
        ))

    def get_pre_create_attr_defs(self):
        groups_enum = [
            {
                "label": group["name"],
                "value": group["group_id"]
            }
            for group in get_groups_data()
            if group["name"]
        ]
        groups_enum.insert(0, {"label": "<Use selection>", "value": -1})

        return [
            EnumDef(
                "group_id",
                label="Group",
                items=groups_enum
            ),
            TextDef(
                "group_name",
                label="New group name",
                placeholder="< Keep unchanged >"
            ),
            BoolDef(
                "mark_for_review",
                label="Review",
                default=self.mark_for_review
            )
        ]

    def get_instance_attr_defs(self):
        groups_enum = [
            {
                "label": group["name"],
                "value": group["group_id"]
            }
            for group in get_groups_data()
            if group["name"]
        ]
        return [
            EnumDef(
                "group_id",
                label="Group",
                items=groups_enum
            ),
            BoolDef(
                "mark_for_review",
                label="Review",
                default=self.mark_for_review
            )
        ]

    def update_instances(self, update_list):
        self._update_renderpass_groups()

        super().update_instances(update_list)

    def _update_renderpass_groups(self):
        render_layer_instances = {}
        render_pass_instances = collections.defaultdict(list)

        for instance in  self.create_context.instances:
            if instance.creator_identifier == CreateRenderPass.identifier:
                render_layer_id = (
                    instance["creator_attributes"]["render_layer_instance_id"]
                )
                render_pass_instances[render_layer_id].append(instance)
            elif instance.creator_identifier == self.identifier:
                render_layer_instances[instance.id] = instance

        if not render_pass_instances or not render_layer_instances:
            return

        layers_data = get_layers_data()
        layers_by_name = collections.defaultdict(list)
        for layer in layers_data:
            layers_by_name[layer["name"]].append(layer)

        george_lines = []
        for render_layer_id, instances in render_pass_instances.items():
            render_layer_inst = render_layer_instances.get(render_layer_id)
            if render_layer_inst is None:
                continue
            group_id = render_layer_inst["creator_attributes"]["group_id"]
            layer_names = set()
            for instance in instances:
                layer_names |= set(instance["layer_names"])

            for layer_name in layer_names:
                george_lines.extend(
                    f"tv_layercolor \"set\" {layer['layer_id']} {group_id}"
                    for layer in layers_by_name[layer_name]
                    if layer["group_id"] != group_id
                )
        if george_lines:
            execute_george_through_file("\n".join(george_lines))


class CreateRenderPass(TVPaintCreator):
    icon = "fa.cube"
    family = "render"
    subset_template_family_filter = "renderPass"
    identifier = "render.pass"
    label = "Render Pass"

    order = CreateRenderlayer.order + 10

    # Settings
    mark_for_review = True

    def get_dynamic_data(
        self, variant, task_name, asset_doc, project_name, host_name, instance
    ):
        dynamic_data = super().get_dynamic_data(
            variant, task_name, asset_doc, project_name, host_name, instance
        )
        dynamic_data["renderpass"] = variant
        dynamic_data["renderlayer"] = "{renderlayer}"
        return dynamic_data

    def create(self, subset_name, instance_data, pre_create_data):
        render_layer_instance_id = pre_create_data.get(
            "render_layer_instance_id"
        )
        if not render_layer_instance_id:
            raise CreatorError("Missing RenderLayer instance")

        render_layer_instance = self.create_context.instances_by_id.get(
            render_layer_instance_id
        )
        if render_layer_instance is None:
            raise CreatorError((
                "RenderLayer instance was not found"
                f" by id \"{render_layer_instance_id}\""
            ))

        group_id = render_layer_instance["creator_attributes"]["group_id"]
        self.log.debug("Query data from workfile.")
        layers_data = get_layers_data()

        self.log.debug("Checking selection.")
        # Get all selected layers and their group ids
        selected_layers = [
            layer
            for layer in layers_data
            if layer["selected"]
        ]

        # Raise if nothing is selected
        if not selected_layers:
            raise CreatorError("Nothing is selected. Please select layers.")

        selected_layer_names = {layer["name"] for layer in selected_layers}
        instances_to_remove = []
        for instance in self.create_context.instances:
            if instance.creator_identifier != self.identifier:
                continue
            layer_names = set(instance["layer_names"])
            if not layer_names.intersection(selected_layer_names):
                continue
            new_layer_names = layer_names - selected_layer_names
            if new_layer_names:
                instance["layer_names"] = list(new_layer_names)
            else:
                instances_to_remove.append(instance)

        render_layer = render_layer_instance["variant"]
        subset_name_fill_data = {"renderlayer": render_layer}

        # Format dynamic keys in subset name
        new_subset_name = subset_name.format(
            **prepare_template_data(subset_name_fill_data)
        )
        self.log.info(f"New subset name is \"{new_subset_name}\".")
        instance_data["layer_names"] = list(selected_layer_names)
        if "creator_attributes" not in instance_data:
            instance_data["creator_attribtues"] = {}

        creator_attributes = instance_data["creator_attribtues"]
        mark_for_review = pre_create_data.get("mark_for_review")
        if mark_for_review is None:
            mark_for_review = self.mark_for_review
        creator_attributes["mark_for_review"] = mark_for_review
        creator_attributes["render_layer_instance_id"] = (
            render_layer_instance_id
        )

        new_instance = CreatedInstance(
            self.family,
            subset_name,
            instance_data,
            self
        )
        instances_data = self._remove_and_filter_instances(
            instances_to_remove
        )
        instances_data.append(new_instance.data_to_store())

        self.host.write_instances(instances_data)
        self._add_instance_to_context(new_instance)
        self._change_layers_group(selected_layers, group_id)

    def _change_layers_group(self, layers, group_id):
        filtered_layers = [
            layer
            for layer in layers
            if layer["group_id"] != group_id
        ]
        if filtered_layers:
            self.log.info((
                "Changing group of "
                f"{','.join([l['name'] for l in filtered_layers])}"
                f" to {group_id}"
            ))
            george_lines = [
                f"tv_layercolor \"set\" {layer['layer_id']} {group_id}"
                for layer in filtered_layers
            ]
            execute_george_through_file("\n".join(george_lines))

    def _remove_and_filter_instances(self, instances_to_remove):
        instances_data = self.host.list_instances()
        if not instances_to_remove:
            return instances_data

        removed_ids = set()
        for instance in instances_to_remove:
            removed_ids.add(instance.id)
            self._remove_instance_from_context(instance)

        return [
            instance_data
            for instance_data in instances_data
            if instance_data.get("instance_id") not in removed_ids
        ]

    def get_pre_create_attr_defs(self):
        render_layers = []
        for instance in self.create_context.instances:
            if instance.creator_identifier == CreateRenderlayer.identifier:
                render_layers.append({
                    "value": instance.id,
                    "label": instance.label
                })

        if not render_layers:
            render_layers.append({"value": None, "label": "N/A"})

        return [
            EnumDef(
                "render_layer_instance_id",
                label="Render Layer",
                items=render_layers
            ),
            BoolDef(
                "mark_for_review",
                label="Review",
                default=self.mark_for_review
            )
        ]

    def get_instance_attr_defs(self):
        return self.get_pre_create_attr_defs()
