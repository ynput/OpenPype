"""
Requires:
    context -> ftrackSession - connected ftrack.Session

Provides:
    context -> ftrackIntentLabel
"""
import json

import six
import pyblish.api


class CollectFtrackIntentLabel(pyblish.api.ContextPlugin):
    """ Collects an ftrack session and the current task id. """

    order = pyblish.api.CollectorOrder + 0.49991
    label = "Collect Ftrack Intent Label"

    def process(self, context):
        intent = context.data.get("intent")
        if intent and isinstance(intent, dict):
            intent_val = intent.get("value")
            intent_label = intent.get("label")
        else:
            intent_val = intent_label = intent

        session = context.data.get("ftrackSession")
        if session is None:
            context.data["ftrackIntentLabel"] = intent_label
            self.log.info("Ftrack session is not available. Skipping.")
            return

        final_intent_label = None
        if intent_val:
            final_intent_label = self.get_intent_label(session, intent_val)

        if final_intent_label is None:
            final_intent_label = intent_label

        context.data["ftrackIntentLabel"] = final_intent_label

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
