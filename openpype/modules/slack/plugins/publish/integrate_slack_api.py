import os
import six
import pyblish.api
import copy

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
        published_path = self._get_thumbnail_path(instance)

        for message_profile in instance.data["slack_channel_message_profiles"]:
            message = self._get_filled_message(message_profile["message"],
                                               instance)
            if not message:
                return

            for channel in message_profile["channels"]:
                if six.PY2:
                    self._python2_call(instance.data["slack_token"],
                                       channel,
                                       message,
                                       published_path,
                                       message_profile["upload_thumbnail"])
                else:
                    self._python3_call(instance.data["slack_token"],
                                       channel,
                                       message,
                                       published_path,
                                       message_profile["upload_thumbnail"])

    def _get_filled_message(self, message_templ, instance):
        """Use message_templ and data from instance to get message content."""
        fill_data = copy.deepcopy(instance.context.data["anatomyData"])

        fill_pairs = (
            ("asset", instance.data.get("asset", fill_data.get("asset"))),
            ("subset", instance.data.get("subset", fill_data.get("subset"))),
            ("task", instance.data.get("task", fill_data.get("task"))),
            ("username", instance.data.get("username",
                                           fill_data.get("username"))),
            ("app", instance.data.get("app", fill_data.get("app"))),
            ("family", instance.data.get("family", fill_data.get("family"))),
            ("version", str(instance.data.get("version",
                                              fill_data.get("version"))))
        )

        multiple_case_variants = prepare_template_data(fill_pairs)
        fill_data.update(multiple_case_variants)

        message = None
        try:
            message = message_templ.format(**fill_data)
        except Exception:
            self.log.warning(
                "Some keys are missing in {}".format(message_templ),
                exc_info=True)

        return message

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

    def _python2_call(self, token, channel, message,
                      published_path, upload_thumbnail):
        from slackclient import SlackClient
        try:
            client = SlackClient(token)
            if upload_thumbnail and \
                    published_path and os.path.exists(published_path):
                with open(published_path, 'rb') as pf:
                    response = client.api_call(
                        "files.upload",
                        channels=channel,
                        initial_comment=message,
                        file=pf,
                        title=os.path.basename(published_path)
                    )
            else:
                response = client.api_call(
                    "chat.postMessage",
                    channel=channel,
                    text=message
                )

            if response.get("error"):
                error_str = self._enrich_error(str(response.get("error")),
                                               channel)
                self.log.warning("Error happened: {}".format(error_str))
        except Exception as e:
            # You will get a SlackApiError if "ok" is False
            error_str = self._enrich_error(str(e), channel)
            self.log.warning("Error happened: {}".format(error_str))

    def _python3_call(self, token, channel, message,
                      published_path, upload_thumbnail):
        from slack_sdk import WebClient
        from slack_sdk.errors import SlackApiError
        try:
            client = WebClient(token=token)
            if upload_thumbnail and \
                    published_path and os.path.exists(published_path):
                _ = client.files_upload(
                    channels=channel,
                    initial_comment=message,
                    file=published_path,
                )
            else:
                _ = client.chat_postMessage(
                    channel=channel,
                    text=message
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
