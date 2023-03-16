import ast

import unreal

from pipeline import (
    create_publish_instance,
    imprint,
)


def new_publish_instance(
        instance_name, path, str_instance_data, str_members
):
    instance_data = ast.literal_eval(str_instance_data)
    members = ast.literal_eval(str_members)

    pub_instance = create_publish_instance(instance_name, path)

    pub_instance.set_editor_property('add_external_assets', True)
    assets = pub_instance.get_editor_property('asset_data_external')

    ar = unreal.AssetRegistryHelpers.get_asset_registry()

    for member in members:
        obj = ar.get_asset_by_object_path(member).get_asset()
        assets.add(obj)

    imprint(f"{path}/{instance_name}", instance_data)
