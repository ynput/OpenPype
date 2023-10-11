# -*- coding: utf-8 -*-
"""Validate if instance asset is the same as context asset."""
from __future__ import absolute_import

import pyblish.api

import openpype.hosts.nuke.api.lib as nlib

from openpype.pipeline.publish import (
    RepairAction,
    ValidateContentsOrder,
    PublishXmlValidationError,
    OptionalPyblishPluginMixin,
    get_errored_instances_from_context
)


class SelectInvalidNodesAction(pyblish.api.Action):
    """Select invalid nodes."""

    label = "Select Failed Node"
    icon = "briefcase"
    on = "failed"

    def process(self, context, plugin):
        if not hasattr(plugin, "select"):
            raise RuntimeError("Plug-in does not have repair method.")

        # Get the failed instances
        self.log.debug("Finding failed plug-ins..")
        failed_instance = get_errored_instances_from_context(context, plugin)
        if failed_instance:
            self.log.debug("Attempting selection ...")
            plugin.select(failed_instance.pop())


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
        SelectInvalidNodesAction,
    ]
    optional = True

    @classmethod
    def apply_settings(cls, project_settings):
        """Apply deprecated settings from project settings.
        """
        nuke_publish = project_settings["nuke"]["publish"]
        if "ValidateCorrectAssetName" not in nuke_publish:
            return

        deprecated_setting = nuke_publish["ValidateCorrectAssetName"]
        cls.enabled = deprecated_setting["enabled"]
        cls.optional = deprecated_setting["optional"]
        cls.active = deprecated_setting["active"]

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        invalid_keys = self.get_invalid(instance, compute=True)

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
    def get_invalid(cls, instance, compute=False):
        """Get invalid keys from instance data and context data."""
        invalid = instance.data.get("invalid_keys", [])

        if compute:
            testing_keys = ["asset", "task"]
            for _key in testing_keys:
                if _key not in instance.data:
                    invalid.append(_key)
                    continue
                if instance.data[_key] != instance.context.data[_key]:
                    invalid.append(_key)

        instance.data["invalid_keys"] = invalid

        return invalid

    @classmethod
    def repair(cls, instance):
        """Repair instance data with context data."""
        invalid = cls.get_invalid(instance)

        create_context = instance.context.data["create_context"]

        instance_id = instance.data.get("instance_id")
        created_instance = create_context.get_instance_by_id(
            instance_id
        )
        for _key in invalid:
            created_instance[_key] = instance.context.data[_key]

        create_context.save_changes()


    @classmethod
    def select(cls, instance):
        """Select invalid node """
        invalid = cls.get_invalid(instance)
        if not invalid:
            return

        select_node = instance.data["transientData"]["node"]
        nlib.reset_selection()
        select_node["selected"].setValue(True)
