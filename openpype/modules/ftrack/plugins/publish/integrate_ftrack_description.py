"""
Requires:
    context > comment
    context > ftrackSession
    instance > ftrackIntegratedAssetVersionsData
"""

import sys

import six
import pyblish.api


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
        # Check if there are any integrated AssetVersion entities
        asset_versions_key = "ftrackIntegratedAssetVersionsData"
        asset_versions_data_by_id = instance.data.get(asset_versions_key)
        if not asset_versions_data_by_id:
            self.log.info("There are any integrated AssetVersions")
            return

        comment = (instance.context.data.get("comment") or "").strip()
        if not comment:
            self.log.info("Comment is not set.")
        else:
            self.log.debug("Comment is set to `{}`".format(comment))

        session = instance.context.data["ftrackSession"]

        intent = instance.context.data.get("intent")
        intent_label = None
        if intent and isinstance(intent, dict):
            intent_val = intent.get("value")
            intent_label = intent.get("label")
        else:
            intent_val = intent

        if not intent_label:
            intent_label = intent_val or ""

        # if intent label is set then format comment
        # - it is possible that intent_label is equal to "" (empty string)
        if intent_label:
            self.log.debug(
                "Intent label is set to `{}`.".format(intent_label)
            )

        else:
            self.log.debug("Intent is not set.")

        for asset_version_data in asset_versions_data_by_id.values():
            asset_version = asset_version_data["asset_version"]

            # Backwards compatibility for older settings using
            #   attribute 'note_with_intent_template'
            comment = self.description_template.format(**{
                "intent": intent_label,
                "comment": comment
            })
            asset_version["comment"] = comment

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
