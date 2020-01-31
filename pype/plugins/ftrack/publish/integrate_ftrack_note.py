import sys
import pyblish.api
import six


class IntegrateFtrackNote(pyblish.api.InstancePlugin):
    """Create comments in Ftrack."""

    # Must be after integrate asset new
    order = pyblish.api.IntegratorOrder + 0.4999
    label = "Integrate Ftrack note"
    families = ["ftrack"]
    optional = True

    def process(self, instance):
        comment = (instance.context.data.get("comment") or "").strip()
        if not comment:
            self.log.info("Comment is not set.")
            return

        self.log.debug("Comment is set to {}".format(comment))

        asset_versions_key = "ftrackIntegratedAssetVersions"
        asset_versions = instance.data.get(asset_versions_key)
        if not asset_versions:
            self.log.info("There are any integrated AssetVersions")
            return

        session = instance.context.data["ftrackSession"]
        user = session.query(
            "User where username is \"{}\"".format(session.api_user)
        ).first()
        if not user:
            self.log.warning(
                "Was not able to query current User {}".format(
                    session.api_user
                )
            )

        for asset_version in asset_versions:
            asset_version.create_note(comment, author=user)

            try:
                session.commit()
                self.log.debug("Note added to AssetVersion \"{}\"".format(
                    str(asset_version)
                ))
            except Exception:
                tp, value, tb = sys.exc_info()
                session.rollback()
                six.reraise(tp, value, tb)
