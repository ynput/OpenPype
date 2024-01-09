"""
Requires:
    context > comment
    context > ftrackSession
    instance > ftrackIntegratedAssetVersionsData
"""

import sys
import json

import six
import pyblish.api
from openpype.lib import StringTemplate


class IntegrateFtrackFromWorkfile(pyblish.api.InstancePlugin):
    """Add source workfile to AssetVersions in Ftrack."""

    # Must be after integrate asset new
    order = pyblish.api.IntegratorOrder + 0.4999
    label = "Integrate Ftrack source workfile"
    families = ["ftrack"]
    optional = True

    def process(self, instance):
        # Check if there are any integrated AssetVersion entities
        asset_versions_key = "ftrackIntegratedAssetVersionsData"
        asset_versions_data_by_id = instance.data.get(asset_versions_key)
        if not asset_versions_data_by_id:
            self.log.info("There are any integrated AssetVersions")
            return

        source = "TEST FOR SOURCE WORKFILE"

        session = instance.context.data["ftrackSession"]
        for asset_version_data in asset_versions_data_by_id.values():
            asset_version = asset_version_data["asset_version"]

            asset_version["custom_attributes"]["fix_fromworkfile"] = source
            self.log.debug(f"ASSET_VERSION_KEYS: {asset_version['custom_attributes'].keys()}")

            try:
                session.commit()
                self.log.debug("Source workfile added to AssetVersion \"{}\"".format(
                    str(asset_version)
                ))
            except Exception:
                tp, value, tb = sys.exc_info()
                session.rollback()
                session._configure_locations()
                six.reraise(tp, value, tb)
