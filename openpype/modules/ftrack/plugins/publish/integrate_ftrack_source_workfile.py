"""
Requires:
    context > comment
    context > ftrackSession
    instance > ftrackIntegratedAssetVersionsData
"""

import sys
import six
from pathlib import Path

from ftrack_api.exception import NoResultFoundError
import pyblish.api

from openpype.settings import get_current_project_settings


class IntegrateFtrackSourceWorkfile(pyblish.api.InstancePlugin):
    """Add source workfile filename to AssetVersions in Ftrack."""

    # Must be after integrate asset new
    order = pyblish.api.IntegratorOrder + 0.4999
    label = "Integrate Ftrack source workfile"
    families = ["ftrack"]
    optional = True

    def process(self, instance):
        task = instance.data.get("ftrackTask")
        name = instance.data.get("name")
        session = instance.context.data["ftrackSession"]

        # Check if there are any integrated AssetVersion entities
        asset_versions_key = "ftrackIntegratedAssetVersionsData"
        asset_versions_key_backwards_compatible = "ftrackIntegratedAssetVersionsData"  # noqa
        asset_version_data = instance.data.get(
            asset_versions_key
        ) or instance.data.get(asset_versions_key_backwards_compatible)
        if not asset_version_data:
            asset_version_data = self.get_asset_version_by_task_id(
                session,
                task['id'],
                name
            )
        else:
            for asset_version in asset_version_data.values():
                asset_version_data = asset_version["asset_version"]

        if not asset_version_data:
            self.log.debug("No AssetVersion found")
            return

        context = instance.context
        filename = context.data["currentFile"]
        is_full_path = get_current_project_settings()["ftrack"]["publish"]["IntegrateFtrackSourceWorkfile"]["full_path"]  # noqa
        if is_full_path:
            filename = str(Path(filename).resolve())
        else:
            filename = Path(filename).name

        asset_version_data["custom_attributes"]["fix_fromworkfile"] = filename

        try:
            session.commit()
            self.log.debug(
                "Source workfile: {} added to AssetVersion \"{}\"".format(
                    filename, str(asset_version_data)
                )
            )
        except Exception:
            tp, value, tb = sys.exc_info()
            session.rollback()
            session._configure_locations()
            six.reraise(tp, value, tb)

    def get_asset_version_by_task_id(self, session, task_id, name):
        try:
            asset_version = session.query(
                f"AssetVersion where task_id is {task_id}"
                " and is_latest_version is True"
                f" and asset has (name is {name})"
            ).one()
        except NoResultFoundError:
            self.log.debug("No AssetVersion found")
            return None

        return asset_version
