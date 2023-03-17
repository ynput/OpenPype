import unreal

import pyblish.api


class ValidateNoDependencies(pyblish.api.InstancePlugin):
    """Ensure that the uasset has no dependencies

    The uasset is checked for dependencies. If there are any, the instance
    cannot be published.
    """

    order = pyblish.api.ValidatorOrder
    label = "Check no dependencies"
    families = ["uasset"]
    hosts = ["unreal"]
    optional = True

    def process(self, instance):
        ar = unreal.AssetRegistryHelpers.get_asset_registry()
        all_dependencies = []

        for obj in instance[:]:
            asset = ar.get_asset_by_object_path(obj)
            dependencies = ar.get_dependencies(
                asset.package_name,
                unreal.AssetRegistryDependencyOptions(
                    include_soft_package_references=False,
                    include_hard_package_references=True,
                    include_searchable_names=False,
                    include_soft_management_references=False,
                    include_hard_management_references=False
                ))
            if dependencies:
                for dep in dependencies:
                    if str(dep).startswith("/Game/"):
                        all_dependencies.append(str(dep))

        if all_dependencies:
            raise RuntimeError(
                f"Dependencies found: {all_dependencies}")
