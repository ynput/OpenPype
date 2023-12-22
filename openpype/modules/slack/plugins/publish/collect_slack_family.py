import pyblish.api

from openpype.lib.profiles_filtering import filter_profiles
from openpype.lib import attribute_definitions
from openpype.pipeline import OpenPypePyblishPluginMixin


class CollectSlackFamilies(pyblish.api.InstancePlugin,
                           OpenPypePyblishPluginMixin):
    """Collect family for Slack notification

        Expects configured profile in
        Project settings > Slack > Publish plugins > Notification to Slack

        Add Slack family to those instance that should be messaged to Slack
    """
    order = pyblish.api.CollectorOrder + 0.4999
    label = 'Collect Slack family'

    profiles = None

    @classmethod
    def get_attribute_defs(cls):
        return [
            attribute_definitions.TextDef(
                # Key under which it will be stored
                "additional_message",
                # Use plugin label as label for attribute
                label="Additional Slack message",
                placeholder="<Only if Slack is configured>"
            )
        ]

    def process(self, instance):
        task_data = instance.data["anatomyData"].get("task", {})
        family = self.main_family_from_instance(instance)
        key_values = {
            "families": family,
            "tasks": task_data.get("name"),
            "task_types": task_data.get("type"),
            "hosts": instance.context.data["hostName"],
            "subsets": instance.data["subset"]
        }
        profile = filter_profiles(self.profiles, key_values,
                                  logger=self.log)

        if not profile:
            self.log.info("No profile found, notification won't be send")
            return

        # make slack publishable
        if not profile:
            return

        self.log.info("Found profile: {}".format(profile))
        if instance.data.get('families'):
            instance.data['families'].append('slack')
        else:
            instance.data['families'] = ['slack']

        selected_profiles = profile["channel_messages"]
        for prof in selected_profiles:
            prof["review_upload_limit"] = profile.get("review_upload_limit",
                                                      50)
        instance.data["slack_channel_message_profiles"] = selected_profiles

        slack_token = (instance.context.data["project_settings"]
                                            ["slack"]
                                            ["token"])
        instance.data["slack_token"] = slack_token

        attribute_values = self.get_attr_values_from_data(instance.data)
        additional_message = attribute_values.get("additional_message")
        if additional_message:
            instance.data["slack_additional_message"] = additional_message

    def main_family_from_instance(self, instance):  # TODO yank from integrate
        """Returns main family of entered instance."""
        family = instance.data.get("family")
        if not family:
            family = instance.data["families"][0]
        return family
