import collections
import pyblish.api
from openpype.pipeline import PublishXmlValidationError


class ValidateRenderLayerGroups(pyblish.api.ContextPlugin):
    """Validate group ids of renderLayer subsets.

    Validate that there are not 2 render layers using the same group.
    """

    label = "Validate Render Layers Group"
    order = pyblish.api.ValidatorOrder + 0.1

    def process(self, context):
        # Prepare layers
        render_layers_by_group_id = collections.defaultdict(list)
        for instance in context:
            families = instance.data.get("families")
            if not families or "renderLayer" not in families:
                continue

            group_id = instance.data["creator_attributes"]["group_id"]
            render_layers_by_group_id[group_id].append(instance)

        duplicated_instances = []
        for group_id, instances in render_layers_by_group_id.items():
            if len(instances) > 1:
                duplicated_instances.append((group_id, instances))

        if not duplicated_instances:
            return

        # Exception message preparations
        groups_data = context.data["groupsData"]
        groups_by_id = {
            group["group_id"]: group
            for group in groups_data
        }

        per_group_msgs = []
        groups_information_lines = []
        for group_id, instances in duplicated_instances:
            group = groups_by_id[group_id]
            group_label = "Group \"{}\" ({})".format(
                group["name"],
                group["group_id"],
            )
            line_join_subset_names = "\n".join([
                f"    - {instance['subset']}"
                for instance in instances
            ])
            joined_subset_names = ", ".join([
                f"\"{instance['subset']}\""
                for instance in instances
            ])
            per_group_msgs.append(
                "{} < {} >".format(group_label, joined_subset_names)
            )
            groups_information_lines.append(
                "<b>{}</b>\n{}".format(group_label, line_join_subset_names)
            )

        # Raise an error
        raise PublishXmlValidationError(
            self,
            (
                "More than one Render Layer is using the same TVPaint"
                " group color. {}"
            ).format(" | ".join(per_group_msgs)),
            formatting_data={
                "groups_information": "\n".join(groups_information_lines)
            }
        )
