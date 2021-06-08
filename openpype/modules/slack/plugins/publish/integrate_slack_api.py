import os
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
        Project settings > Slack > Publish plugins > Notification to Slack.

        If instance contains 'thumbnail' it uploads it. Bot must be present
        in the target channel.

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

        published_path = self._get_thumbnail_path(instance)

        for channel in instance.data["slack_channel"]:
            if python2:
                self._python2_call(instance.data["slack_token"],
                                   channel,
                                   message,
                                   published_path)
            else:
                self._python3_call(instance.data["slack_token"],
                                   channel,
                                   message,
                                   published_path)

    def _get_thumbnail_path(self, instance):
        """Returns abs url for thumbnail if present in instance repres"""
        published_path = None
        for comp in instance.data['representations']:
            self.log.debug('component {}'.format(comp))

            if comp.get('thumbnail') or ("thumbnail" in comp.get('tags', [])):
                self.log.debug("thumbnail present")

                comp_files = comp["files"]
                if isinstance(comp_files, (tuple, list, set)):
                    filename = comp_files[0]
                else:
                    filename = comp_files

                published_path = os.path.join(
                    comp['stagingDir'], filename
                )
                break
        return published_path

    def _python2_call(self, token, channel, message, published_path):
        try:
            client = SlackClient(token)
            if not published_path:
                response = client.api_call(
                    "chat.postMessage",
                    channel=channel,
                    text=message
                )
            else:
                response = client.api_call(
                    "files.upload",
                    channels=channel,
                    initial_comment=message,
                    file=published_path,
                )
            if response.get("error"):
                error_str = self._enrich_error(str(response.get("error")),
                                               channel)
                self.log.warning("Error happened: {}".format(error_str))
        except Exception as e:
            # You will get a SlackApiError if "ok" is False
            error_str = self._enrich_error(str(e), channel)
            self.log.warning("Error happened: {}".format(error_str))

    def _python3_call(self, token, channel, message, published_path):
        try:
            client = WebClient(token=token)
            if not published_path:
                _ = client.chat_postMessage(
                    channel=channel,
                    text=message
                )
            else:
                _ = client.files_upload(
                    channels=channel,
                    initial_comment=message,
                    file=published_path,
                )
        except SlackApiError as e:
            # You will get a SlackApiError if "ok" is False
            error_str = self._enrich_error(str(e.response["error"]), channel)
            self.log.warning("Error happened {}".format(error_str))

    def _enrich_error(self, error_str, channel):
        """Enhance known errors with more helpful notations."""
        if 'not_in_channel' in error_str:
            # there is no file.write.public scope, app must be explicitly in
            # the channel
            msg = " - application must added to channel '{}'.".format(channel)
            error_str += msg + " Ask Slack admin."

        return error_str
