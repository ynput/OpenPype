from openpype.pipeline import legacy_io
from openpype.pipeline.create.creator_plugins import SubsetConvertorPlugin
from openpype.hosts.maya.api import plugin


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
        for identifier, creator in self.create_context.manual_creators.items():
            family = getattr(creator, "family", None)
            if not family:
                continue

            if family in family_to_id:
                # We have a clash of family -> identifier. Multiple
                # new style creators use the same family
                self.log.warning("Clash on family->identifier: "
                                 "{}".format(identifier))
            family_to_id[family] = identifier

        # We also embed the current 'task' into the instance since legacy
        # instances didn't store that data on the instances. The old style
        # logic was thus to be live to the current task to begin with.
        data = dict()
        data["task"] = legacy_io.Session.get("AVALON_TASK")
        for family, instance_nodes in legacy.items():
            if family in family_to_id:
                # We only imprint the creator identifier for it to identify
                # as the new style creator
                creator_id = family_to_id[family]
                data["creator_identifier"] = creator_id
                for instance_node in instance_nodes:
                    self.imprint_instance_node(instance_node,
                                               data=data.copy())
