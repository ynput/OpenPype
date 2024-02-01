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

There is special case for simple publishing of scene which is called
'render.scene'. That will use all visible layers and render them as one big
sequence.

Todos:
    Add option to extract marked layers and passes as json output format for
        AfterEffects.
"""

import collections
from typing import Any, Optional, Union

from openpype import AYON_SERVER_ENABLED
from openpype.client import get_asset_by_name, get_asset_name_identifier
from openpype.lib import (
    prepare_template_data,
    AbstractAttrDef,
    UILabelDef,
    UISeparatorDef,
    EnumDef,
    TextDef,
    BoolDef,
)
from openpype.pipeline.create import (
    CreatedInstance,
    CreatorError,
)
from openpype.hosts.tvpaint.api.plugin import (
    TVPaintCreator,
    TVPaintAutoCreator,
)
from openpype.hosts.tvpaint.api.lib import (
    get_layers_data,
    get_groups_data,
    execute_george_through_file,
)

RENDER_LAYER_DETAILED_DESCRIPTIONS = (
    """Render Layer is "a group of TVPaint layers"

Be aware Render Layer <b>is not</b> TVPaint layer.

All TVPaint layers in the scene with the color group id are rendered in the
beauty pass. To create sub passes use Render Pass creator which is
dependent on existence of render layer instance.

The group can represent an asset (tree) or different part of scene that consist
of one or more TVPaint layers that can be used as single item during
compositing (for example).

In some cases may be needed to have sub parts of the layer. For example 'Bob'
could be Render Layer which has 'Arm', 'Head' and 'Body' as Render Passes.
"""
)


RENDER_PASS_DETAILED_DESCRIPTIONS = (
    """Render Pass is sub part of Render Layer.

Render Pass can consist of one or more TVPaint layers. Render Pass must
belong to a Render Layer. Marked TVPaint layers will change it's group color
to match group color of Render Layer.
"""
)


AUTODETECT_RENDER_DETAILED_DESCRIPTION = (
    """Semi-automated Render Layer and Render Pass creation.

Based on information in TVPaint scene will be created Render Layers and Render
Passes. All color groups used in scene will be used for Render Layer creation.
Name of the group is used as a variant.

All TVPaint layers under the color group will be created as Render Pass where
layer name is used as variant.

The plugin will use all used color groups and layers, or can skip those that
are not visible.

There is option to auto-rename color groups before Render Layer creation. That
is based on settings template where is filled index of used group from bottom
to top.
"""
)

class CreateRenderlayer(TVPaintCreator):
    """Mark layer group as Render layer instance.

    All TVPaint layers in the scene with the color group id are rendered in the
    beauty pass. To create sub passes use Render Layer creator which is
    dependent on existence of render layer instance.
    """

    label = "Render Layer"
    family = "render"
    subset_template_family_filter = "renderLayer"
    identifier = "render.layer"
    icon = "fa5.images"

    # George script to change color group
    rename_script_template = (
        "tv_layercolor \"setcolor\""
        " {clip_id} {group_id} {r} {g} {b} \"{name}\""
    )
    # Order to be executed before Render Pass creator
    order = 90
    description = "Mark TVPaint color group as one Render Layer."
    detailed_description = RENDER_LAYER_DETAILED_DESCRIPTIONS

    # Settings
    # - Default render pass name for beauty
    default_pass_name = "beauty"
    # - Mark by default instance for review
    mark_for_review = True

    def apply_settings(self, project_settings):
        plugin_settings = (
            project_settings["tvpaint"]["create"]["create_render_layer"]
        )
        self.default_variant = plugin_settings["default_variant"]
        self.default_variants = plugin_settings["default_variants"]
        self.default_pass_name = plugin_settings["default_pass_name"]
        self.mark_for_review = plugin_settings["mark_for_review"]

    def get_dynamic_data(
        self, variant, task_name, asset_doc, project_name, host_name, instance
    ):
        dynamic_data = super().get_dynamic_data(
            variant, task_name, asset_doc, project_name, host_name, instance
        )
        dynamic_data["renderpass"] = self.default_pass_name
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

        group_name = instance_data["variant"]
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

        if not group_id or group_item["name"] == group_name:
            return new_instance

        self.log.debug("Changing name of the group.")
        # Rename TVPaint group (keep color same)
        # - groups can't contain spaces
        rename_script = self.rename_script_template.format(
            clip_id=group_item["clip_id"],
            group_id=group_item["group_id"],
            r=group_item["red"],
            g=group_item["green"],
            b=group_item["blue"],
            name=group_name
        )
        execute_george_through_file(rename_script)

        self.log.info((
            f"Name of group with index {group_id}"
            f" was changed to \"{group_name}\"."
        ))
        return new_instance

    def _get_groups_enum(self):
        groups_enum = []
        empty_groups = []
        for group in get_groups_data():
            group_name = group["name"]
            item = {
                "label": group_name,
                "value": group["group_id"]
            }
            # TVPaint have defined how many color groups is available, but
            #   the count is not consistent across versions. It is not possible
            #   to know how many groups there is.
            #
            if group_name and group_name != "0":
                if empty_groups:
                    groups_enum.extend(empty_groups)
                    empty_groups = []
                groups_enum.append(item)
            else:
                empty_groups.append(item)
        return groups_enum

    def get_pre_create_attr_defs(self):
        groups_enum = self._get_groups_enum()
        groups_enum.insert(0, {"label": "<Use selection>", "value": -1})

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

    def get_instance_attr_defs(self):
        groups_enum = self._get_groups_enum()
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
        self._update_color_groups()
        self._update_renderpass_groups()

        super().update_instances(update_list)

    def _update_color_groups(self):
        render_layer_instances = []
        for instance in self.create_context.instances:
            if instance.creator_identifier == self.identifier:
                render_layer_instances.append(instance)

        if not render_layer_instances:
            return

        groups_by_id = {
            group["group_id"]: group
            for group in get_groups_data()
        }
        grg_script_lines = []
        for instance in render_layer_instances:
            group_id = instance["creator_attributes"]["group_id"]
            variant = instance["variant"]
            group = groups_by_id[group_id]
            if group["name"] == variant:
                continue

            grg_script_lines.append(self.rename_script_template.format(
                clip_id=group["clip_id"],
                group_id=group["group_id"],
                r=group["red"],
                g=group["green"],
                b=group["blue"],
                name=variant
            ))

        if grg_script_lines:
            execute_george_through_file("\n".join(grg_script_lines))

    def _update_renderpass_groups(self):
        render_layer_instances = {}
        render_pass_instances = collections.defaultdict(list)

        for instance in self.create_context.instances:
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
    family = "render"
    subset_template_family_filter = "renderPass"
    identifier = "render.pass"
    label = "Render Pass"
    icon = "fa5.image"
    description = "Mark selected TVPaint layers as pass of Render Layer."
    detailed_description = RENDER_PASS_DETAILED_DESCRIPTIONS

    order = CreateRenderlayer.order + 10

    # Settings
    mark_for_review = True

    def apply_settings(self, project_settings):
        plugin_settings = (
            project_settings["tvpaint"]["create"]["create_render_pass"]
        )
        self.default_variant = plugin_settings["default_variant"]
        self.default_variants = plugin_settings["default_variants"]
        self.mark_for_review = plugin_settings["mark_for_review"]

    def collect_instances(self):
        instances_by_identifier = self._cache_and_get_instances()
        render_layers = {
            instance_data["instance_id"]: {
                "variant": instance_data["variant"],
                "template_data": prepare_template_data({
                    "renderlayer": instance_data["variant"]
                })
            }
            for instance_data in (
                instances_by_identifier[CreateRenderlayer.identifier]
            )
        }

        for instance_data in instances_by_identifier[self.identifier]:
            render_layer_instance_id = (
                instance_data
                .get("creator_attributes", {})
                .get("render_layer_instance_id")
            )
            render_layer_info = render_layers.get(render_layer_instance_id, {})
            self.update_instance_labels(
                instance_data,
                render_layer_info.get("variant"),
                render_layer_info.get("template_data")
            )
            instance = CreatedInstance.from_existing(instance_data, self)
            self._add_instance_to_context(instance)

    def get_dynamic_data(
        self, variant, task_name, asset_doc, project_name, host_name, instance
    ):
        dynamic_data = super().get_dynamic_data(
            variant, task_name, asset_doc, project_name, host_name, instance
        )
        dynamic_data["renderpass"] = variant
        dynamic_data["renderlayer"] = "{renderlayer}"
        return dynamic_data

    def update_instance_labels(
        self, instance, render_layer_variant, render_layer_data=None
    ):
        old_label = instance.get("label")
        old_group = instance.get("group")
        new_label = None
        new_group = None
        if render_layer_variant is not None:
            if render_layer_data is None:
                render_layer_data = prepare_template_data({
                    "renderlayer": render_layer_variant
                })
            try:
                new_label = instance["subset"].format(**render_layer_data)
            except (KeyError, ValueError):
                pass

            new_group = f"{self.get_group_label()} ({render_layer_variant})"

        instance["label"] = new_label
        instance["group"] = new_group
        return old_group != new_group or old_label != new_label

    def create(self, subset_name, instance_data, pre_create_data):
        render_layer_instance_id = pre_create_data.get(
            "render_layer_instance_id"
        )
        if not render_layer_instance_id:
            raise CreatorError((
                "You cannot create a Render Pass without a Render Layer."
                " Please select one first"
            ))

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
        marked_layer_names = pre_create_data.get("layer_names")
        if marked_layer_names is not None:
            layers_by_name = {layer["name"]: layer for layer in layers_data}
            marked_layers = []
            for layer_name in marked_layer_names:
                layer = layers_by_name.get(layer_name)
                if layer is None:
                    raise CreatorError(
                        f"Layer with name \"{layer_name}\" was not found")
                marked_layers.append(layer)

        else:
            marked_layers = [
                layer
                for layer in layers_data
                if layer["selected"]
            ]

            # Raise if nothing is selected
            if not marked_layers:
                raise CreatorError(
                    "Nothing is selected. Please select layers.")

            marked_layer_names = {layer["name"] for layer in marked_layers}

        marked_layer_names = set(marked_layer_names)

        instances_to_remove = []
        for instance in self.create_context.instances:
            if instance.creator_identifier != self.identifier:
                continue
            cur_layer_names = set(instance["layer_names"])
            if not cur_layer_names.intersection(marked_layer_names):
                continue
            new_layer_names = cur_layer_names - marked_layer_names
            if new_layer_names:
                instance["layer_names"] = list(new_layer_names)
            else:
                instances_to_remove.append(instance)

        render_layer = render_layer_instance["variant"]
        subset_name_fill_data = {"renderlayer": render_layer}

        # Format dynamic keys in subset name
        label = subset_name
        try:
            label = label.format(
                **prepare_template_data(subset_name_fill_data)
            )
        except (KeyError, ValueError):
            pass

        self.log.info(f"New subset name is \"{label}\".")
        instance_data["label"] = label
        instance_data["group"] = f"{self.get_group_label()} ({render_layer})"
        instance_data["layer_names"] = list(marked_layer_names)
        if "creator_attributes" not in instance_data:
            instance_data["creator_attributes"] = {}

        creator_attributes = instance_data["creator_attributes"]
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
        self._change_layers_group(marked_layers, group_id)

        return new_instance

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
        # Find available Render Layers
        # - instances are created after creators reset
        current_instances = self.host.list_instances()
        render_layers = [
            {
                "value": inst["instance_id"],
                "label": inst["subset"]
            }
            for inst in current_instances
            if inst.get("creator_identifier") == CreateRenderlayer.identifier
        ]
        if not render_layers:
            render_layers.append({"value": None, "label": "N/A"})

        return [
            EnumDef(
                "render_layer_instance_id",
                label="Render Layer",
                items=render_layers
            ),
            UILabelDef(
                "NOTE: Try to hit refresh if you don't see a Render Layer"
            ),
            BoolDef(
                "mark_for_review",
                label="Review",
                default=self.mark_for_review
            )
        ]

    def get_instance_attr_defs(self):
        # Find available Render Layers
        current_instances = self.create_context.instances
        render_layers = [
            {
                "value": instance.id,
                "label": instance.label
            }
            for instance in current_instances
            if instance.creator_identifier == CreateRenderlayer.identifier
        ]
        if not render_layers:
            render_layers.append({"value": None, "label": "N/A"})

        return [
            EnumDef(
                "render_layer_instance_id",
                label="Render Layer",
                items=render_layers
            ),
            UILabelDef(
                "NOTE: Try to hit refresh if you don't see a Render Layer"
            ),
            BoolDef(
                "mark_for_review",
                label="Review",
                default=self.mark_for_review
            )
        ]


class TVPaintAutoDetectRenderCreator(TVPaintCreator):
    """Create Render Layer and Render Pass instances based on scene data.

    This is auto-detection creator which can be triggered by user to create
    instances based on information in scene. Each used color group in scene
    will be created as Render Layer where group name is used as variant and
    each TVPaint layer as Render Pass where layer name is used as variant.

    Never will have any instances, all instances belong to different creators.
    """

    family = "render"
    label = "Render Layer/Passes"
    identifier = "render.auto.detect.creator"
    order = CreateRenderPass.order + 10
    description = (
        "Create Render Layers and Render Passes based on scene setup"
    )
    detailed_description = AUTODETECT_RENDER_DETAILED_DESCRIPTION

    # Settings
    enabled = False
    allow_group_rename = True
    group_name_template = "L{group_index}"
    group_idx_offset = 10
    group_idx_padding = 3

    def apply_settings(self, project_settings):
        plugin_settings = (
            project_settings
            ["tvpaint"]
            ["create"]
            ["auto_detect_render"]
        )
        self.enabled = plugin_settings.get("enabled", False)
        self.allow_group_rename = plugin_settings["allow_group_rename"]
        self.group_name_template = plugin_settings["group_name_template"]
        self.group_idx_offset = plugin_settings["group_idx_offset"]
        self.group_idx_padding = plugin_settings["group_idx_padding"]

    def _rename_groups(
        self,
        groups_order: list[int],
        scene_groups: list[dict[str, Any]]
    ):
        new_group_name_by_id: dict[int, str] = {}
        groups_by_id: dict[int, dict[str, Any]] = {
            group["group_id"]: group
            for group in scene_groups
        }
        # Count only renamed groups
        for idx, group_id in enumerate(groups_order):
            group_index_value: str = (
                "{{:0>{}}}"
                .format(self.group_idx_padding)
                .format((idx + 1) * self.group_idx_offset)
            )
            group_name_fill_values: dict[str, str] = {
                "groupIdx": group_index_value,
                "groupidx": group_index_value,
                "group_idx": group_index_value,
                "group_index": group_index_value,
            }

            group_name: str = self.group_name_template.format(
                **group_name_fill_values
            )
            group: dict[str, Any] = groups_by_id[group_id]
            if group["name"] != group_name:
                new_group_name_by_id[group_id] = group_name

        grg_lines: list[str] = []
        for group_id, group_name in new_group_name_by_id.items():
            group: dict[str, Any] = groups_by_id[group_id]
            grg_line: str = "tv_layercolor \"setcolor\" {} {} {} {} {}".format(
                group["clip_id"],
                group_id,
                group["red"],
                group["green"],
                group["blue"],
                group_name
            )
            grg_lines.append(grg_line)
            group["name"] = group_name

        if grg_lines:
            execute_george_through_file("\n".join(grg_lines))

    def _prepare_render_layer(
        self,
        project_name: str,
        asset_doc: dict[str, Any],
        task_name: str,
        group_id: int,
        groups: list[dict[str, Any]],
        mark_for_review: bool,
        existing_instance: Optional[CreatedInstance] = None,
    ) -> Union[CreatedInstance, None]:
        match_group: Union[dict[str, Any], None] = next(
            (
                group
                for group in groups
                if group["group_id"] == group_id
            ),
            None
        )
        if not match_group:
            return None

        variant: str = match_group["name"]
        creator: CreateRenderlayer = (
            self.create_context.creators[CreateRenderlayer.identifier]
        )

        subset_name: str = creator.get_subset_name(
            variant,
            task_name,
            asset_doc,
            project_name,
            host_name=self.create_context.host_name,
        )
        asset_name = get_asset_name_identifier(asset_doc)
        if existing_instance is not None:
            if AYON_SERVER_ENABLED:
                existing_instance["folderPath"] = asset_name
            else:
                existing_instance["asset"] = asset_name
            existing_instance["task"] = task_name
            existing_instance["subset"] = subset_name
            return existing_instance

        instance_data: dict[str, str] = {
            "task": task_name,
            "family": creator.family,
            "variant": variant
        }
        if AYON_SERVER_ENABLED:
            instance_data["folderPath"] = asset_name
        else:
            instance_data["asset"] = asset_name
        pre_create_data: dict[str, str] = {
            "group_id": group_id,
            "mark_for_review": mark_for_review
        }
        return creator.create(subset_name, instance_data, pre_create_data)

    def _prepare_render_passes(
        self,
        project_name: str,
        asset_doc: dict[str, Any],
        task_name: str,
        render_layer_instance: CreatedInstance,
        layers: list[dict[str, Any]],
        mark_for_review: bool,
        existing_render_passes: list[CreatedInstance]
    ):
        creator: CreateRenderPass = (
            self.create_context.creators[CreateRenderPass.identifier]
        )
        render_pass_by_layer_name = {}
        for render_pass in existing_render_passes:
            for layer_name in render_pass["layer_names"]:
                render_pass_by_layer_name[layer_name] = render_pass

        asset_name = get_asset_name_identifier(asset_doc)

        for layer in layers:
            layer_name = layer["name"]
            variant = layer_name
            render_pass = render_pass_by_layer_name.get(layer_name)
            if render_pass is not None:
                if (render_pass["layer_names"]) > 1:
                    variant = render_pass["variant"]

            subset_name = creator.get_subset_name(
                variant,
                task_name,
                asset_doc,
                project_name,
                host_name=self.create_context.host_name,
                instance=render_pass
            )

            if render_pass is not None:
                if AYON_SERVER_ENABLED:
                    render_pass["folderPath"] = asset_name
                else:
                    render_pass["asset"] = asset_name

                render_pass["task"] = task_name
                render_pass["subset"] = subset_name
                continue

            instance_data: dict[str, str] = {
                "task": task_name,
                "family": creator.family,
                "variant": variant
            }
            if AYON_SERVER_ENABLED:
                instance_data["folderPath"] = asset_name
            else:
                instance_data["asset"] = asset_name

            pre_create_data: dict[str, Any] = {
                "render_layer_instance_id": render_layer_instance.id,
                "layer_names": [layer_name],
                "mark_for_review": mark_for_review
            }
            creator.create(subset_name, instance_data, pre_create_data)

    def _filter_groups(
        self,
        layers_by_group_id,
        groups_order,
        only_visible_groups
    ):
        new_groups_order = []
        for group_id in groups_order:
            layers: list[dict[str, Any]] = layers_by_group_id[group_id]
            if not layers:
                continue

            if (
                only_visible_groups
                and not any(
                    layer
                    for layer in layers
                    if layer["visible"]
                )
            ):
                continue
            new_groups_order.append(group_id)
        return new_groups_order

    def create(self, subset_name, instance_data, pre_create_data):
        project_name: str = self.create_context.get_current_project_name()
        if AYON_SERVER_ENABLED:
            asset_name: str = instance_data["folderPath"]
        else:
            asset_name: str = instance_data["asset"]
        task_name: str = instance_data["task"]
        asset_doc: dict[str, Any] = get_asset_by_name(
            project_name, asset_name)

        render_layers_by_group_id: dict[int, CreatedInstance] = {}
        render_passes_by_render_layer_id: dict[int, list[CreatedInstance]] = (
            collections.defaultdict(list)
        )
        for instance in self.create_context.instances:
            if instance.creator_identifier == CreateRenderlayer.identifier:
                group_id = instance["creator_attributes"]["group_id"]
                render_layers_by_group_id[group_id] = instance
            elif instance.creator_identifier == CreateRenderPass.identifier:
                render_layer_id = (
                    instance
                    ["creator_attributes"]
                    ["render_layer_instance_id"]
                )
                render_passes_by_render_layer_id[render_layer_id].append(
                    instance
                )

        layers_by_group_id: dict[int, list[dict[str, Any]]] = (
            collections.defaultdict(list)
        )
        scene_layers: list[dict[str, Any]] = get_layers_data()
        scene_groups: list[dict[str, Any]] = get_groups_data()
        groups_order: list[int] = []
        for layer in scene_layers:
            group_id: int = layer["group_id"]
            # Skip 'default' group
            if group_id == 0:
                continue

            layers_by_group_id[group_id].append(layer)
            if group_id not in groups_order:
                groups_order.append(group_id)

        groups_order.reverse()

        mark_layers_for_review = pre_create_data.get(
            "mark_layers_for_review", False
        )
        mark_passes_for_review = pre_create_data.get(
            "mark_passes_for_review", False
        )
        rename_groups = pre_create_data.get("rename_groups", False)
        only_visible_groups = pre_create_data.get("only_visible_groups", False)
        groups_order = self._filter_groups(
            layers_by_group_id,
            groups_order,
            only_visible_groups
        )
        if not groups_order:
            return

        if rename_groups:
            self._rename_groups(groups_order, scene_groups)

        # Make sure  all render layers are created
        for group_id in groups_order:
            instance: Union[CreatedInstance, None] = (
                self._prepare_render_layer(
                    project_name,
                    asset_doc,
                    task_name,
                    group_id,
                    scene_groups,
                    mark_layers_for_review,
                    render_layers_by_group_id.get(group_id),
                )
            )
            if instance is not None:
                render_layers_by_group_id[group_id] = instance

        for group_id in groups_order:
            layers: list[dict[str, Any]] = layers_by_group_id[group_id]
            render_layer_instance: Union[CreatedInstance, None] = (
                render_layers_by_group_id.get(group_id)
            )
            if not layers or render_layer_instance is None:
                continue

            self._prepare_render_passes(
                project_name,
                asset_doc,
                task_name,
                render_layer_instance,
                layers,
                mark_passes_for_review,
                render_passes_by_render_layer_id[render_layer_instance.id]
            )

    def get_pre_create_attr_defs(self) -> list[AbstractAttrDef]:
        render_layer_creator: CreateRenderlayer = (
            self.create_context.creators[CreateRenderlayer.identifier]
        )
        render_pass_creator: CreateRenderPass = (
            self.create_context.creators[CreateRenderPass.identifier]
        )
        output = []
        if self.allow_group_rename:
            output.extend([
                BoolDef(
                    "rename_groups",
                    label="Rename color groups",
                    tooltip="Will rename color groups using studio template",
                    default=True
                ),
                BoolDef(
                    "only_visible_groups",
                    label="Only visible color groups",
                    tooltip=(
                        "Render Layers and rename will happen only on color"
                        " groups with visible layers."
                    ),
                    default=True
                ),
                UISeparatorDef()
            ])
        output.extend([
            BoolDef(
                "mark_layers_for_review",
                label="Mark RenderLayers for review",
                default=render_layer_creator.mark_for_review
            ),
            BoolDef(
                "mark_passes_for_review",
                label="Mark RenderPasses for review",
                default=render_pass_creator.mark_for_review
            )
        ])
        return output


class TVPaintSceneRenderCreator(TVPaintAutoCreator):
    family = "render"
    subset_template_family_filter = "renderScene"
    identifier = "render.scene"
    label = "Scene Render"
    icon = "fa.file-image-o"

    # Settings
    default_pass_name = "beauty"
    mark_for_review = True
    active_on_create = False

    def apply_settings(self, project_settings):
        plugin_settings = (
            project_settings["tvpaint"]["create"]["create_render_scene"]
        )
        self.default_variant = plugin_settings["default_variant"]
        self.default_variants = plugin_settings["default_variants"]
        self.mark_for_review = plugin_settings["mark_for_review"]
        self.active_on_create = plugin_settings["active_on_create"]
        self.default_pass_name = plugin_settings["default_pass_name"]

    def get_dynamic_data(self, variant, *args, **kwargs):
        dynamic_data = super().get_dynamic_data(variant, *args, **kwargs)
        dynamic_data["renderpass"] = "{renderpass}"
        dynamic_data["renderlayer"] = variant
        return dynamic_data

    def _create_new_instance(self):
        create_context = self.create_context
        host_name = create_context.host_name
        project_name = create_context.get_current_project_name()
        asset_name = create_context.get_current_asset_name()
        task_name = create_context.get_current_task_name()

        asset_doc = get_asset_by_name(project_name, asset_name)
        subset_name = self.get_subset_name(
            self.default_variant,
            task_name,
            asset_doc,
            project_name,
            host_name
        )
        data = {
            "task": task_name,
            "variant": self.default_variant,
            "creator_attributes": {
                "render_pass_name": self.default_pass_name,
                "mark_for_review": True
            },
            "label": self._get_label(
                subset_name,
                self.default_pass_name
            )
        }
        if AYON_SERVER_ENABLED:
            data["folderPath"] = asset_name
        else:
            data["asset"] = asset_name
        if not self.active_on_create:
            data["active"] = False

        new_instance = CreatedInstance(
            self.family, subset_name, data, self
        )
        instances_data = self.host.list_instances()
        instances_data.append(new_instance.data_to_store())
        self.host.write_instances(instances_data)
        self._add_instance_to_context(new_instance)
        return new_instance

    def create(self):
        existing_instance = None
        for instance in self.create_context.instances:
            if instance.creator_identifier == self.identifier:
                existing_instance = instance
                break

        if existing_instance is None:
            return self._create_new_instance()

        create_context = self.create_context
        host_name = create_context.host_name
        project_name = create_context.get_current_project_name()
        asset_name = create_context.get_current_asset_name()
        task_name = create_context.get_current_task_name()

        existing_name = None
        if AYON_SERVER_ENABLED:
            existing_name = existing_instance.get("folderPath")
        if existing_name is None:
            existing_name = existing_instance["asset"]

        if (
            existing_name != asset_name
            or existing_instance["task"] != task_name
        ):
            asset_doc = get_asset_by_name(project_name, asset_name)
            subset_name = self.get_subset_name(
                existing_instance["variant"],
                task_name,
                asset_doc,
                project_name,
                host_name,
                existing_instance
            )
            if AYON_SERVER_ENABLED:
                existing_instance["folderPath"] = asset_name
            else:
                existing_instance["asset"] = asset_name
            existing_instance["task"] = task_name
            existing_instance["subset"] = subset_name

        existing_instance["label"] = self._get_label(
            existing_instance["subset"],
            existing_instance["creator_attributes"]["render_pass_name"]
        )

    def _get_label(self, subset_name, render_pass_name):
        try:
            subset_name = subset_name.format(**prepare_template_data({
                "renderpass": render_pass_name
            }))
        except (KeyError, ValueError):
            pass

        return subset_name

    def get_instance_attr_defs(self):
        return [
            TextDef(
                "render_pass_name",
                label="Pass Name",
                default=self.default_pass_name,
                tooltip=(
                    "Value is calculated during publishing and UI will update"
                    " label after refresh."
                )
            ),
            BoolDef(
                "mark_for_review",
                label="Review",
                default=self.mark_for_review
            )
        ]
