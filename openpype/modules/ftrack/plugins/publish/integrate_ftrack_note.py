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
    note_template = None
    # Backwards compatibility
    note_with_intent_template = "{intent}: {comment}"
    # - note label must exist in Ftrack
    note_labels = []

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
        if intent and isinstance(intent, dict):
            intent_val = intent.get("value")
            intent_label = intent.get("label")
        else:
            intent_val = intent_label = intent

        final_intent_label = None
        if intent_val:
            final_intent_label = self.get_intent_label(session, intent_val)

        if final_intent_label is None:
            final_intent_label = intent_label

        # if intent label is set then format comment
        # - it is possible that intent_label is equal to "" (empty string)
        if final_intent_label:
            self.log.debug(
                "Intent label is set to `{}`.".format(final_intent_label)
            )

        elif intent_val:
            self.log.debug((
                "Intent is set to `{}` and was not added"
                " to comment because label is set to `{}`."
            ).format(intent_val, final_intent_label))

        else:
            self.log.debug("Intent is not set.")

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
            all_labels = session.query("select id, name from NoteLabel").all()
            labels_by_low_name = {lab["name"].lower(): lab for lab in all_labels}
            for _label in self.note_labels:
                label = labels_by_low_name.get(_label.lower())
                if not label:
                    self.log.warning(
                        "Note Label `{}` was not found.".format(_label)
                    )
                    continue

                labels.append(label)

        for asset_version_data in asset_versions_data_by_id.values():
            asset_version = asset_version_data["asset_version"]
            component_items = asset_version_data["component_items"]

            published_paths = set()
            for component_item in component_items:
                published_paths.add(component_item["component_path"])

            # Backwards compatibility for older settings using
            #   attribute 'note_with_intent_template'
            template = self.note_template
            if template is None:
                template = self.note_with_intent_template
            format_data = {
                "intent": final_intent_label,
                "comment": comment,
                "published_paths": "\n".join(sorted(published_paths))
            }
            comment = template.format(**format_data)
            if not comment:
                self.log.info((
                    "Note for AssetVersion {} would be empty. Skipping."
                    "\nTemplate: {}\nData: {}"
                ).format(asset_version["id"], template, format_data))
                continue
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

        if isinstance(items, six.string_types):
            items = json.loads(items)

        intent_label = None
        for item in items:
            if item["value"] == intent_value:
                intent_label = item["menu"]
                break

        return intent_label
