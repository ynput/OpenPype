import logging

from openpype.pipeline.context_tools import _get_modules_manager as get_modules_manager


log = logging.getLogger(__name__)


def get_latest_tracked_version_number(instance, task_name):
    """Get the latest version of the instance on the active tracker else None.
    Args:
        instance (dict): The instance whose version is to be retrieved.
        task_name (str): Name of the instance's task.
    """
    version_number = None
    modules_manager = get_modules_manager()

    # Tracker modules
    ftrack_module = modules_manager.modules_by_name.get("ftrack")
    kitsu_module = modules_manager.modules_by_name.get("kitsu")

    if ftrack_module and ftrack_module.enabled:
        asset_name = instance.data["subset"]
        asset_ftrack_id = instance.data["assetEntity"]["data"].get("ftrackId")
        version_number = (
            ftrack_module.get_asset_latest_version_number(
                asset_ftrack_id,
                task_name,
                asset_name
            )
        )
    elif kitsu_module and kitsu_module.enabled:
        # TODO: add support for Kitsu
        pass
    # Add additional tracker support here

    return version_number
