import logging

from openpype.pipeline.context_tools import _get_modules_manager as get_modules_manager


log = logging.getLogger(__name__)


def get_latest_version_number(instance, task_name):
    """Get the latest version of the instance on ftrack.
    Args:
        instance (dict): The instance whose version is to be retrieved.
        task_name (str): Name of the instance's task.
    """
    subset = instance.data["subset"]
    asset_ftrack_id = instance.data["assetEntity"]["data"].get("ftrackId")
    if not asset_ftrack_id:
        log.info((
            "Asset does not have filled ftrack id. Skipped getting"
            " ftrack latest version."
        ))
        return

    # Check if ftrack module is enabled
    modules_manager = get_modules_manager()
    ftrack_module = modules_manager.modules_by_name.get("ftrack")
    if not ftrack_module or not ftrack_module.enabled:
        return

    import ftrack_api

    session = ftrack_api.Session()
    asset = session.query(
        f"Asset where parent.id is '{asset_ftrack_id}'"
        f" and latest_version.task.name is '{task_name}'"
        f" and name like '%{subset}%'"
    ).first()

    if asset:
        return asset["latest_version"]["version"]

    return None
