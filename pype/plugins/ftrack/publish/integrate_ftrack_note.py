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

    # Can be set in presets:
    # - Allows only `intent` and `comment` keys
    note_with_intent_template = "{intent}: {comment}"
    # - note label must exist in Ftrack
    note_labels = []

    def process(self, instance):
        comment = (instance.context.data.get("comment") or "").strip()
        if not comment:
            self.log.info("Comment is not set.")
            return

        self.log.debug("Comment is set to `{}`".format(comment))

        intent = instance.context.data.get("intent")
        if intent:
            msg = "Intent is set to `{}` and was added to comment.".format(
                intent
            )
            comment = self.note_with_intent_template.format(**{
                "intent": intent,
                "comment": comment
            })
        else:
            msg = "Intent is not set."
        self.log.debug(msg)

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

        labels = []
        if self.note_labels:
            all_labels = session.query("NoteLabel").all()
            labels_by_low_name = {lab["name"].lower(): lab for lab in all_labels}
            for _label in self.note_labels:
                label = labels_by_low_name.get(_label.lower())
                if not label:
                    self.log.warning(
                        "Note Label `{}` was not found.".format(_label)
                    )
                    continue

                labels.append(label)

        for asset_version in asset_versions:
            asset_version.create_note(comment, author=user, labels=labels)

            try:
                session.commit()
                self.log.debug("Note added to AssetVersion \"{}\"".format(
                    str(asset_version)
                ))
            except Exception:
                tp, value, tb = sys.exc_info()
                session.rollback()
                six.reraise(tp, value, tb)
