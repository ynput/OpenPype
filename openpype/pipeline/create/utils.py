import collections

from openpype.client import (
    get_assets,
    get_subsets,
    get_last_versions,
    get_asset_name_identifier,
)


def get_last_versions_for_instances(
    project_name, instances, use_value_for_missing=False
):
    """Get last versions for instances by their asset and subset name.

    Args:
        project_name (str): Project name.
        instances (list[CreatedInstance]): Instances to get next versions for.
        use_value_for_missing (Optional[bool]): Missing values are replaced
            with negative value if True. Otherwise None is used. -2 is used
            for instances without filled asset or subset name. -1 is used
            for missing entities.

    Returns:
        dict[str, Union[int, None]]: Last versions by instance id.
    """

    output = {
        instance.id: -1 if use_value_for_missing else None
        for instance in instances
    }
    subset_names_by_asset_name = collections.defaultdict(set)
    instances_by_hierarchy = {}
    for instance in instances:
        asset_name = instance.data.get("asset")
        subset_name = instance.subset_name
        if not asset_name or not subset_name:
            if use_value_for_missing:
                output[instance.id] = -2
            continue

        (
            instances_by_hierarchy
            .setdefault(asset_name, {})
            .setdefault(subset_name, [])
            .append(instance)
        )
        subset_names_by_asset_name[asset_name].add(subset_name)

    subset_names = set()
    for names in subset_names_by_asset_name.values():
        subset_names |= names

    if not subset_names:
        return output

    asset_docs = get_assets(
        project_name,
        asset_names=subset_names_by_asset_name.keys(),
        fields=["name", "_id", "data.parents"]
    )
    asset_names_by_id = {
        asset_doc["_id"]: get_asset_name_identifier(asset_doc)
        for asset_doc in asset_docs
    }
    if not asset_names_by_id:
        return output

    subset_docs = get_subsets(
        project_name,
        asset_ids=asset_names_by_id.keys(),
        subset_names=subset_names,
        fields=["_id", "name", "parent"]
    )
    subset_docs_by_id = {}
    for subset_doc in subset_docs:
        # Filter subset docs by subset names under parent
        asset_id = subset_doc["parent"]
        asset_name = asset_names_by_id[asset_id]
        subset_name = subset_doc["name"]
        if subset_name not in subset_names_by_asset_name[asset_name]:
            continue
        subset_docs_by_id[subset_doc["_id"]] = subset_doc

    if not subset_docs_by_id:
        return output

    last_versions_by_subset_id = get_last_versions(
        project_name,
        subset_docs_by_id.keys(),
        fields=["name", "parent"]
    )
    for subset_id, version_doc in last_versions_by_subset_id.items():
        subset_doc = subset_docs_by_id[subset_id]
        asset_id = subset_doc["parent"]
        asset_name = asset_names_by_id[asset_id]
        _instances = instances_by_hierarchy[asset_name][subset_doc["name"]]
        for instance in _instances:
            output[instance.id] = version_doc["name"]

    return output


def get_next_versions_for_instances(project_name, instances):
    """Get next versions for instances by their asset and subset name.

    Args:
        project_name (str): Project name.
        instances (list[CreatedInstance]): Instances to get next versions for.

    Returns:
        dict[str, Union[int, None]]: Next versions by instance id. Version is
            'None' if instance has no asset or subset name.
    """

    last_versions = get_last_versions_for_instances(
        project_name, instances, True)

    output = {}
    for instance_id, version in last_versions.items():
        if version == -2:
            output[instance_id] = None
        elif version == -1:
            output[instance_id] = 1
        else:
            output[instance_id] = version + 1
    return output
