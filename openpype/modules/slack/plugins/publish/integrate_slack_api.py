try:
    from slackclient import SlackClient
    python2 = True
except ImportError:
    python2 = False
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError

import pyblish.api
from openpype.lib.plugin_tools import prepare_template_data


class IntegrateSlackAPI(pyblish.api.InstancePlugin):
    """ Send message notification to a channel.

        Triggers on instances with "slack" family, filled by
        'collect_slack_family'.

        Expects configured profile in
        Project settings > Slack > Publish plugins > Notification to Slack

        Message template can contain {} placeholders from anatomyData.
    """
    order = pyblish.api.IntegratorOrder + 0.499
    label = "Integrate Slack Api"
    families = ["slack"]

    optional = True

    def process(self, instance):
        message_templ = instance.data["slack_message"]

        fill_pairs = set()
        for key, value in instance.data["anatomyData"].items():
            if not isinstance(value, str):
                continue
            fill_pairs.add((key, value))

        message = message_templ.format(**prepare_template_data(fill_pairs))

        self.log.debug("message:: {}".format(message))
        if '{' in message:
            self.log.warning(
                "Missing values to fill message properly {}".format(message))

            return

        for channel in instance.data["slack_channel"]:
            if python2:
                self._python2_call(instance.data["slack_token"],
                                   channel,
                                   message)
            else:
                self._python3_call(instance.data["slack_token"],
                                   channel,
                                   message)

    def _python2_call(self, token, channel, message):
        try:
            client = SlackClient(token)
            response = client.api_call(
                "chat.postMessage",
                channel=channel,
                text=message
            )
            if response.get("error"):
                self.log.warning("Error happened: {}".format(
                    response.get("error")))
        except Exception as e:
            # You will get a SlackApiError if "ok" is False
            self.log.warning("Error happened: {}".format(str(e)))

    def _python3_call(self, token, channel, message):
        try:
            client = WebClient(token=token)
            _ = client.chat_postMessage(
                channel=channel,
                text=message
            )
        except SlackApiError as e:
            # You will get a SlackApiError if "ok" is False
            self.log.warning("Error happened {}".format(e.response[
                                                            "error"]))
