from avalon import io
import pyblish.api

from openpype.lib.profiles_filtering import filter_profiles


class CollectSlackFamilies(pyblish.api.InstancePlugin):
    """Collect family for Slack notification

        Expects configured profile in
        Project settings > Slack > Publish plugins > Notification to Slack

        Add Slack family to those instance that should be messaged to Slack
    """
    order = pyblish.api.CollectorOrder + 0.4999
    label = 'Collect Slack family'

    profiles = None

    def process(self, instance):
        task_name = io.Session.get("AVALON_TASK")
        family = self.main_family_from_instance(instance)

        key_values = {
            "families": family,
            "tasks": task_name,
            "hosts": instance.data["anatomyData"]["app"],
        }
        self.log.debug("key_values {}".format(key_values))
        profile = filter_profiles(self.profiles, key_values,
                                  logger=self.log)

        # make slack publishable
        if profile:
            if instance.data.get('families'):
                instance.data['families'].append('slack')
            else:
                instance.data['families'] = ['slack']

            instance.data["slack_channel"] = profile["channel"]
            instance.data["slack_message"] = profile["message"]

            slack_token = (instance.context.data["project_settings"]
                                                ["slack"]
                                                ["publish"]
                                                ["CollectSlackFamilies"]
                                                ["token"])
            instance.data["slack_token"] = slack_token

    def main_family_from_instance(self, instance):  # TODO yank from integrate
        """Returns main family of entered instance."""
        family = instance.data.get("family")
        if not family:
            family = instance.data["families"][0]
        return family
