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

        fill_pairs = (
            ("project_name", instance.data["anatomyData"]["project"]["name"]),
            ("project_code", instance.data["anatomyData"]["project"]["code"]),
            ("asset", instance.data["anatomyData"]["asset"]),
            ("subset", instance.data["anatomyData"]["subset"]),
            ("task", instance.data["anatomyData"]["task"]),
            ("username", instance.data["anatomyData"]["username"]),
            ("app", instance.data["anatomyData"]["app"]),
            ("family", instance.data["anatomyData"]["family"]),
            ("version", str(instance.data["anatomyData"]["version"])),
        )
        message = None
        try:
            message = message_templ.format(
                **prepare_template_data(fill_pairs))
        except Exception:
            self.log.warning(
                "Some keys are missing in {}".format(message_templ),
                exc_info=True)

        self.log.debug("message:: {}".format(message))

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
        for repre in instance.data['representations']:
            if repre.get('thumbnail') or "thumbnail" in repre.get('tags', []):

                repre_files = repre["files"]
                if isinstance(repre_files, (tuple, list, set)):
                    filename = repre_files[0]
                else:
                    filename = repre_files

                published_path = os.path.join(
                    repre['stagingDir'], filename
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
