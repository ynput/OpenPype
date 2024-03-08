"""
Requires:
    context > comment
    context > ftrackSession
    instance > ftrackIntegratedAssetVersionsData
"""

import sys
import six
from pathlib import Path

import pyblish.api

from openpype.settings import get_current_project_settings
from openpype.modules.ftrack import get_asset_versions_by_task_id


class IntegrateFtrackSourceWorkfile(pyblish.api.InstancePlugin):
    """Add source workfile filename to AssetVersions in Ftrack."""

    # Must be after integrate asset new
    order = pyblish.api.IntegratorOrder + 0.5000
    label = "Integrate Ftrack source workfile"
    families = ["ftrack"]
    optional = True

    def process(self, instance):
        # TODO: rework that to properly do the job, this doesn't work in a bunch of cases
        # No time to fix it, I added protections to avoid crashes
        task = instance.data.get("ftrackTask")
        name = instance.data.get("name")
        session = instance.context.data["ftrackSession"]

        # Check if there are any integrated AssetVersion entities
        asset_versions_key = "ftrackIntegratedAssetVersionsData"
        asset_versions_data_by_id = instance.data.get(asset_versions_key, {})

        if not asset_versions_data_by_id:
            # Backwards compatibility
            asset_versions_alt_key = "ftrackIntegratedAssetVersions"
            asset_versions_data_by_id = instance.data.get(asset_versions_alt_key, {})

        if not asset_versions_data_by_id:
            # Last way to try retrieving the asset versions
            asset_versions_data_by_id = get_asset_versions_by_task_id(
                session, task['id'], name)

        if not asset_versions_data_by_id:
            self.log.debug("No AssetVersion found")
            return

        # Get the workfile name or fullpath
        workfile = instance.context.data["currentFile"]
        is_full_path = get_current_project_settings()["ftrack"]["publish"]["IntegrateFtrackSourceWorkfile"]["full_path"]  # noqa
        if is_full_path:
            workfile = str(Path(workfile).resolve())
        else:
            workfile = Path(workfile).name

        # Add it to the asset version
        if not isinstance(asset_versions_data_by_id, dict):
            # TODO: This code has been added to avoid crash but this isn't a fix
            return

        for asset_version_data in asset_versions_data_by_id.values():
            asset_version = asset_version_data["asset_version"]
            asset_version["custom_attributes"]["fix_fromworkfile"] = workfile

            try:
                session.commit()
                self.log.debug(
                    "Source workfile: {} added to AssetVersion \"{}\"".format(
                        workfile, str(asset_version_data)
                    )
                )
            except Exception: # noqa
                tp, value, tb = sys.exc_info()
                session.rollback()
                session._configure_locations()
                six.reraise(tp, value, tb)
