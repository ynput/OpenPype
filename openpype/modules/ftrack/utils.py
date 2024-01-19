from ftrack_api.exception import NoResultFoundError


def get_asset_version_by_task_id(session, task_id, name):
    try:
        asset_version = session.query(
            f"AssetVersion where task_id is {task_id}"
            " and is_latest_version is True"
            f" and asset has (name is {name})"
        ).one()
    except NoResultFoundError:
        return None

    return asset_version
