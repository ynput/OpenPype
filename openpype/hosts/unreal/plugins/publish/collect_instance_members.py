import unreal

import pyblish.api


class CollectInstanceMembers(pyblish.api.InstancePlugin):
    """
    Collect members of instance.

    This collector will collect the assets for the families that support to
    have them included as External Data, and will add them to the instance
    as members.
    """

    order = pyblish.api.CollectorOrder + 0.1
    hosts = ["unreal"]
    families = ["camera", "look", "unrealStaticMesh", "uasset"]
    label = "Collect Instance Members"

    def process(self, instance):
        """Collect members of instance."""
        self.log.info("Collecting instance members")

        ar = unreal.AssetRegistryHelpers.get_asset_registry()

        inst_path = instance.data.get('instance_path')
        inst_name = instance.data.get('objectName')

        pub_instance = ar.get_asset_by_object_path(
            f"{inst_path}.{inst_name}").get_asset()

        if not pub_instance:
            self.log.error(f"{inst_path}.{inst_name}")
            raise RuntimeError(f"Instance {instance} not found.")

        if not pub_instance.get_editor_property("add_external_assets"):
            # No external assets in the instance
            return

        assets = pub_instance.get_editor_property('asset_data_external')

        members = [asset.get_path_name() for asset in assets]

        self.log.debug(f"Members: {members}")

        instance.data["members"] = members
