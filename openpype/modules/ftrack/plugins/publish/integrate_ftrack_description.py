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


class IntegrateFtrackDescription(pyblish.api.InstancePlugin):
    """Add description to AssetVersions in Ftrack."""

    # Must be after integrate asset new
    order = pyblish.api.IntegratorOrder + 0.4999
    label = "Integrate Ftrack description"
    families = ["ftrack"]
    optional = True

    # Can be set in settings:
    # - Allows `intent` and `comment` keys
    description_template = "{comment}"

    def process(self, instance):
        if not self.description_template:
            self.log.info("Skipping. Description template is not set.")
            return

        # Check if there are any integrated AssetVersion entities
        asset_versions_key = "ftrackIntegratedAssetVersionsData"
        asset_versions_data_by_id = instance.data.get(asset_versions_key)
        if not asset_versions_data_by_id:
            self.log.info("There are any integrated AssetVersions")
            return

        comment = instance.data["comment"]
        if not comment:
            self.log.debug("Comment is not set.")
        else:
            self.log.debug("Comment is set to `{}`".format(comment))

        intent = instance.context.data.get("intent")
        if intent and "{intent}" in self.description_template:
            value = intent.get("value")
            if value:
                intent = intent.get("label") or value

        if not intent and not comment:
            self.log.info("Skipping. Intent and comment are empty.")
            return

        # if intent label is set then format comment
        # - it is possible that intent_label is equal to "" (empty string)
        if intent:
            self.log.debug("Intent is set to `{}`.".format(intent))
        else:
            self.log.debug("Intent is not set.")

        # If we would like to use more "optional" possibilities we would have
        #   come up with some expressions in templates or speicifc templates
        #   for all 3 possible combinations when comment and intent are
        #   set or not (when both are not set then description does not
        #   make sense).
        fill_data = {}
        if comment:
            fill_data["comment"] = comment
        if intent:
            fill_data["intent"] = intent

        description = StringTemplate.format_template(
            self.description_template, fill_data
        )
        if not description.solved:
            self.log.warning((
                "Couldn't solve template \"{}\" with data {}"
            ).format(
                self.description_template, json.dumps(fill_data, indent=4)
            ))
            return

        if not description:
            self.log.debug((
                "Skipping. Result of template is empty string."
                " Template \"{}\" Fill data: {}"
            ).format(
                self.description_template, json.dumps(fill_data, indent=4)
            ))
            return

        session = instance.context.data["ftrackSession"]
        for asset_version_data in asset_versions_data_by_id.values():
            asset_version = asset_version_data["asset_version"]

            # Backwards compatibility for older settings using
            #   attribute 'note_with_intent_template'

            asset_version["comment"] = description

            try:
                session.commit()
                self.log.debug("Comment added to AssetVersion \"{}\"".format(
                    str(asset_version)
                ))
            except Exception:
                tp, value, tb = sys.exc_info()
                session.rollback()
                session._configure_locations()
                six.reraise(tp, value, tb)
