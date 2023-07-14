from openpype.pipeline.create.creator_plugins import SubsetConvertorPlugin
from openpype.hosts.maya.api import plugin
from openpype.hosts.maya.api.lib import read

from maya import cmds
from maya.app.renderSetup.model import renderSetup


class MayaLegacyConvertor(SubsetConvertorPlugin,
                          plugin.MayaCreatorBase):
    """Find and convert any legacy subsets in the scene.

    This Convertor will find all legacy subsets in the scene and will
    transform them to the current system. Since the old subsets doesn't
    retain any information about their original creators, the only mapping
    we can do is based on their families.

    Its limitation is that you can have multiple creators creating subset
    of the same family and there is no way to handle it. This code should
    nevertheless cover all creators that came with OpenPype.

    """
    identifier = "io.openpype.creators.maya.legacy"

    # Cases where the identifier or new family doesn't correspond to the
    # original family on the legacy instances
    special_family_conversions = {
        "rendering": "io.openpype.creators.maya.renderlayer",
    }

    def find_instances(self):

        self.cache_subsets(self.collection_shared_data)
        legacy = self.collection_shared_data.get("maya_cached_legacy_subsets")
        if not legacy:
            return

        self.add_convertor_item("Convert legacy instances")

    def convert(self):
        self.remove_convertor_item()

        # We can't use the collected shared data cache here
        # we re-query it here directly to convert all found.
        cache = {}
        self.cache_subsets(cache)
        legacy = cache.get("maya_cached_legacy_subsets")
        if not legacy:
            return

        # From all current new style manual creators find the mapping
        # from family to identifier
        family_to_id = {}
        # Consider both disabled and enabled creators e.g. the "animation"
        # creator is disabled to be hidden from the user.
        for identifier, creator in self.create_context.creators.items():
            family = getattr(creator, "family", None)
            if not family:
                continue

            if family in family_to_id:
                # We have a clash of family -> identifier. Multiple
                # new style creators use the same family
                self.log.warning("Clash on family->identifier: "
                                 "{}".format(identifier))
            family_to_id[family] = identifier

        family_to_id.update(self.special_family_conversions)

        # We also embed the current 'task' into the instance since legacy
        # instances didn't store that data on the instances. The old style
        # logic was thus to be live to the current task to begin with.
        data = dict()
        data["task"] = self.create_context.get_current_task_name()
        for family, instance_nodes in legacy.items():
            if family not in family_to_id:
                self.log.warning(
                    "Unable to convert legacy instance with family '{}'"
                    " because there is no matching new creator's family"
                    "".format(family)
                )
                continue

            creator_id = family_to_id[family]
            creator = self.create_context.creators[creator_id]
            data["creator_identifier"] = creator_id

            if isinstance(creator, plugin.RenderlayerCreator):
                self._convert_per_renderlayer(instance_nodes, data, creator)
            else:
                self._convert_regular(instance_nodes, data)

    def _convert_regular(self, instance_nodes, data):
        # We only imprint the creator identifier for it to identify
        # as the new style creator
        for instance_node in instance_nodes:
            self.imprint_instance_node(instance_node,
                                       data=data.copy())

    def _convert_per_renderlayer(self, instance_nodes, data, creator):
        # Split the instance into an instance per layer
        rs = renderSetup.instance()
        layers = rs.getRenderLayers()
        if not layers:
            self.log.error(
                "Can't convert legacy renderlayer instance because no existing"
                " renderSetup layers exist in the scene."
            )
            return

        creator_attribute_names = {
            attr_def.key for attr_def in creator.get_instance_attr_defs()
        }

        for instance_node in instance_nodes:

            # Ensure we have the new style singleton node generated
            # TODO: Make function public
            singleton_node = creator._get_singleton_node()
            if singleton_node:
                self.log.error(
                    "Can't convert legacy renderlayer instance '{}' because"
                    " new style instance '{}' already exists".format(
                        instance_node,
                        singleton_node
                    )
                )
                continue

            creator.create_singleton_node()

            # We are creating new nodes to replace the original instance
            # Copy the attributes of the original instance to the new node
            original_data = read(instance_node)

            # The family gets converted to the new family (this is due to
            # "rendering" family being converted to "renderlayer" family)
            original_data["family"] = creator.family

            # Convert to creator attributes when relevant
            creator_attributes = {}
            for key in list(original_data.keys()):
                # Iterate in order of the original attributes to preserve order
                # in the output creator attributes
                if key in creator_attribute_names:
                    creator_attributes[key] = original_data.pop(key)
            original_data["creator_attributes"] = creator_attributes

            # For layer in maya layers
            for layer in layers:
                layer_instance_node = creator.find_layer_instance_node(layer)
                if not layer_instance_node:
                    # TODO: Make function public
                    layer_instance_node = creator._create_layer_instance_node(
                        layer
                    )

                # Transfer the main attributes of the original instance
                layer_data = original_data.copy()
                layer_data.update(data)

                self.imprint_instance_node(layer_instance_node,
                                           data=layer_data)

            # Delete the legacy instance node
            cmds.delete(instance_node)
