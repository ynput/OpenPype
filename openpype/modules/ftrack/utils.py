from ftrack_api.exception import NoResultFoundError


def get_asset_versions_by_task_id(session, task_id, name):
    try:
        asset_versions = session.query(
            f"AssetVersion where task_id is {task_id}"
            " and is_latest_version is True"
            f" and asset has (name is {name})"
        ).all()
    except NoResultFoundError:
        return []

    return asset_versions
