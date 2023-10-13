# -*- coding: utf-8 -*-
"""Validate if instance asset is the same as context asset."""
from __future__ import absolute_import

import pyblish.api

from openpype.pipeline.publish import (
    RepairAction,
    ValidateContentsOrder,
    PublishXmlValidationError,
    OptionalPyblishPluginMixin
)
from openpype.hosts.nuke.api import SelectInstanceNodeAction


class ValidateCorrectAssetContext(
    pyblish.api.InstancePlugin,
    OptionalPyblishPluginMixin
):
    """Validator to check if instance asset context match context asset.

    When working in per-shot style you always publish data in context of
    current asset (shot). This validator checks if this is so. It is optional
    so it can be disabled when needed.

    Checking `asset` and `task` keys.
    """
    order = ValidateContentsOrder
    label = "Validate asset context"
    hosts = ["nuke"]
    actions = [
        RepairAction,
        SelectInstanceNodeAction
    ]
    optional = True

    @classmethod
    def apply_settings(cls, project_settings):
        """Apply deprecated settings from project settings.
        """
        nuke_publish = project_settings["nuke"]["publish"]
        if "ValidateCorrectAssetName" in nuke_publish:
            settings = nuke_publish["ValidateCorrectAssetName"]
        else:
            settings = nuke_publish["ValidateCorrectAssetContext"]

        cls.enabled = settings["enabled"]
        cls.optional = settings["optional"]
        cls.active = settings["active"]

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        invalid_keys = self.get_invalid(instance)

        if not invalid_keys:
            return

        message_values = {
            "node_name": instance.data["transientData"]["node"].name(),
            "correct_values": ", ".join([
                "{} > {}".format(_key, instance.context.data[_key])
                for _key in invalid_keys
            ]),
            "wrong_values": ", ".join([
                "{} > {}".format(_key, instance.data.get(_key))
                for _key in invalid_keys
            ])
        }

        msg = (
            "Instance `{node_name}` has wrong context keys:\n"
            "Correct: `{correct_values}` | Wrong: `{wrong_values}`").format(
                **message_values)

        self.log.debug(msg)

        raise PublishXmlValidationError(
            self, msg, formatting_data=message_values
        )

    @classmethod
    def get_invalid(cls, instance):
        """Get invalid keys from instance data and context data."""

        invalid_keys = []
        testing_keys = ["asset", "task"]
        for _key in testing_keys:
            if _key not in instance.data:
                invalid_keys.append(_key)
                continue
            if instance.data[_key] != instance.context.data[_key]:
                invalid_keys.append(_key)

        return invalid_keys

    @classmethod
    def repair(cls, instance):
        """Repair instance data with context data."""
        invalid_keys = cls.get_invalid(instance)

        create_context = instance.context.data["create_context"]

        instance_id = instance.data.get("instance_id")
        created_instance = create_context.get_instance_by_id(
            instance_id
        )
        for _key in invalid_keys:
            created_instance[_key] = instance.context.data[_key]

        create_context.save_changes()
