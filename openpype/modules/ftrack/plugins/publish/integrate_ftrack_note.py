import sys
import json
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

    def get_intent_label(self, session, intent_value):
        if not intent_value:
            return

        intent_configurations = session.query(
            "CustomAttributeConfiguration where key is intent"
        ).all()
        if not intent_configurations:
            return

        intent_configuration = intent_configurations[0]
        if len(intent_configuration) > 1:
            self.log.warning((
                "Found more than one `intent` custom attribute."
                " Using first found."
            ))

        config = intent_configuration.get("config")
        if not config:
            return

        configuration = json.loads(config)
        items = configuration.get("data")
        if not items:
            return

        if sys.version_info[0] < 3:
            string_type = basestring
        else:
            string_type = str

        if isinstance(items, string_type):
            items = json.loads(items)

        intent_label = None
        for item in items:
            if item["value"] == intent_value:
                intent_label = item["menu"]
                break

        return intent_label

    def process(self, instance):
        comment = (instance.context.data.get("comment") or "").strip()
        if not comment:
            self.log.info("Comment is not set.")
            return

        self.log.debug("Comment is set to `{}`".format(comment))

        session = instance.context.data["ftrackSession"]

        intent = instance.context.data.get("intent")
        if intent and isinstance(intent, dict):
            intent_val = intent.get("value")
            intent_label = intent.get("label")
        else:
            intent_val = intent_label = intent

        final_label = None
        if intent_val:
            final_label = self.get_intent_label(session, intent_val)
            if final_label is None:
                final_label = intent_label

        # if intent label is set then format comment
        # - it is possible that intent_label is equal to "" (empty string)
        if final_label:
            msg = "Intent label is set to `{}`.".format(final_label)
            comment = self.note_with_intent_template.format(**{
                "intent": final_label,
                "comment": comment
            })

        elif intent_val:
            msg = (
                "Intent is set to `{}` and was not added"
                " to comment because label is set to `{}`."
            ).format(intent_val, final_label)

        else:
            msg = "Intent is not set."

        self.log.debug(msg)

        asset_versions_key = "ftrackIntegratedAssetVersions"
        asset_versions = instance.data.get(asset_versions_key)
        if not asset_versions:
            self.log.info("There are any integrated AssetVersions")
            return

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
                session._configure_locations()
                six.reraise(tp, value, tb)
