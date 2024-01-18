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
        asset_version = None
        version = 0
        session = instance.context.data["ftrackSession"]

        asset_versions = session.query(f"AssetVersion where task_id is \"{task['id']}\"").all()
        for asset in asset_versions:
            if asset['asset']['name'] == name:
                if asset['version'] > version:
                    version = asset['version']
                    asset_version = asset

        if asset_version:
            self.log.debug(f"ASSET VERSION: {asset_version['asset']['name']}, VERSION: {asset_version['version']}")

        # Check if there are any integrated AssetVersion entities
        # asset_versions_key = "ftrackIntegratedAssetVersionsData"
        # asset_versions_data_by_id = instance.data.get(asset_versions_key)
        # if not asset_versions_data_by_id:
        #     # for asset in instance.data["ftrackEntity"].get("assets"):
        #     #     self.log.debug(f"ASSET: {asset['name']}")
        #     asset_versions_key = "ftrackIntegratedAssetVersions"
        #     asset_versions_data_by_id = instance.data.get(asset_versions_key)
        #     if not asset_versions_data_by_id:
        #         self.log.info("There are any integrated AssetVersions")
        #         return
        #     else:
        #         self.log.debug("Using old key: {}".format(asset_versions_data_by_id))

        # context = instance.context
        # filename = context.data["currentFile"]
        # is_full_path = get_current_project_settings()["ftrack"]["publish"]["IntegrateFtrackSourceWorkfile"]["full_path"]
        # if is_full_path:
        #     filename = str(Path(filename).resolve())
        # else:
        #     filename = Path(filename).name

        # session = instance.context.data["ftrackSession"]
        # for asset_version_data in asset_versions_data_by_id.values():
        #     asset_version = asset_version_data["asset_version"]
        #     asset_version["custom_attributes"]["fix_fromworkfile"] = filename

        #     try:
        #         session.commit()
        #         self.log.debug("Source workfile: {} added to AssetVersion \"{}\"".format(
        #             filename, str(asset_version)
        #         ))
        #     except Exception:
        #         tp, value, tb = sys.exc_info()
        #         session.rollback()
        #         session._configure_locations()
        #         six.reraise(tp, value, tb)
