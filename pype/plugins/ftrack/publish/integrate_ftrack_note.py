import sys
import pyblish.api
import six


class IntegrateFtrackNote(pyblish.api.InstancePlugin):
    """Create comments in Ftrack."""

    order = pyblish.api.IntegratorOrder
    label = "Integrate Comments to Ftrack."
    families = ["ftrack"]
    optional = True

    def process(self, instance):
        comment = (instance.context.data.get("comment") or "").strip()
        if not comment:
            return

        asset_versions_key = "ftrackIntegratedAssetVersions"
        asset_versions = instance.data.get(asset_versions_key)
        if not asset_versions:
            return

        session = context.data["ftrackSession"]

        note = session.create("Note", {"content": comment})
        for asset_version in asset_versions:
            asset_version["notes"].extend(note)

            try:
                session.commit()
            except Exception:
                tp, value, tb = sys.exc_info()
                session.rollback()
                six.reraise(tp, value, tb)
