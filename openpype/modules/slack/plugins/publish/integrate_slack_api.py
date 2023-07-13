import os
import re
import six
import pyblish.api
import copy
from datetime import datetime
from abc import ABCMeta, abstractmethod
import time

from openpype.client import OpenPypeMongoConnection
from openpype.pipeline.publish import get_publish_repre_path
from openpype.lib.plugin_tools import prepare_template_data


class IntegrateSlackAPI(pyblish.api.InstancePlugin):
    """ Send message notification to a channel.
        Triggers on instances with "slack" family, filled by
        'collect_slack_family'.
        Expects configured profile in
        Project settings > Slack > Publish plugins > Notification to Slack.
        If instance contains 'thumbnail' it uploads it. Bot must be present
        in the target channel.
        If instance contains 'review' it could upload (if configured) or place
        link with {review_filepath} placeholder.
        Message template can contain {} placeholders from anatomyData.
    """
    order = pyblish.api.IntegratorOrder + 0.499
    label = "Integrate Slack Api"
    families = ["slack"]

    optional = True

    def process(self, instance):
        thumbnail_path = self._get_thumbnail_path(instance)
        review_path = self._get_review_path(instance)

        publish_files = set()
        message = ''
        additional_message = instance.data.get("slack_additional_message")
        token = instance.data["slack_token"]
        if additional_message:
            message = "{} \n".format(additional_message)
        users = groups = None
        for message_profile in instance.data["slack_channel_message_profiles"]:
            message += self._get_filled_message(message_profile["message"],
                                                instance,
                                                review_path)
            if not message:
                return

            if message_profile["upload_thumbnail"] and thumbnail_path:
                publish_files.add(thumbnail_path)

            if message_profile["upload_review"] and review_path:
                message, publish_files = self._handle_review_upload(
                    message, message_profile, publish_files, review_path)

            project = instance.context.data["anatomyData"]["project"]["code"]
            for channel in message_profile["channels"]:
                if six.PY2:
                    client = SlackPython2Operations(token, self.log)
                else:
                    client = SlackPython3Operations(token, self.log)

                if "@" in message:
                    cache_key = "__cache_slack_ids"
                    slack_ids = instance.context.data.get(cache_key, None)
                    if slack_ids is None:
                        users, groups = client.get_users_and_groups()
                        instance.context.data[cache_key] = {}
                        instance.context.data[cache_key]["users"] = users
                        instance.context.data[cache_key]["groups"] = groups
                    else:
                        users = slack_ids["users"]
                        groups = slack_ids["groups"]
                    message = self._translate_users(message, users, groups)

                msg_id, file_ids = client.send_message(channel,
                                                       message,
                                                       publish_files)
                if not msg_id:
                    return

                msg = {
                    "type": "slack",
                    "msg_id": msg_id,
                    "file_ids": file_ids,
                    "project": project,
                    "created_dt": datetime.now()
                }
                mongo_client = OpenPypeMongoConnection.get_mongo_client()
                database_name = os.environ["OPENPYPE_DATABASE_NAME"]
                dbcon = mongo_client[database_name]["notification_messages"]
                dbcon.insert_one(msg)

    def _handle_review_upload(self, message, message_profile, publish_files,
                              review_path):
        """Check if uploaded file is not too large"""
        review_file_size_MB = os.path.getsize(review_path) / 1024 / 1024
        file_limit = message_profile.get("review_upload_limit", 50)
        if review_file_size_MB > file_limit:
            message += "\nReview upload omitted because of file size."
            if review_path not in message:
                message += "\nFile located at: {}".format(review_path)
        else:
            publish_files.add(review_path)
        return message, publish_files

    def _get_filled_message(self, message_templ, instance, review_path=None):
        """Use message_templ and data from instance to get message content.

        Reviews might be large, so allow only adding link to message instead of
        uploading only.
        """

        fill_data = copy.deepcopy(instance.context.data["anatomyData"])

        username = fill_data.get("user")
        fill_pairs = [
            ("asset", instance.data.get("asset", fill_data.get("asset"))),
            ("subset", instance.data.get("subset", fill_data.get("subset"))),
            ("user", username),
            ("username", username),
            ("app", instance.data.get("app", fill_data.get("app"))),
            ("family", instance.data.get("family", fill_data.get("family"))),
            ("version", str(instance.data.get("version",
                                              fill_data.get("version"))))
        ]
        if review_path:
            fill_pairs.append(("review_filepath", review_path))

        task_data = (
                copy.deepcopy(instance.data.get("anatomyData", {})).get("task")
                or fill_data.get("task")
        )
        if not isinstance(task_data, dict):
            # fallback for legacy - if task_data is only task name
            task_data["name"] = task_data
        if task_data:
            if (
                "{task}" in message_templ
                or "{Task}" in message_templ
                or "{TASK}" in message_templ
            ):
                fill_pairs.append(("task", task_data["name"]))

            else:
                for key, value in task_data.items():
                    fill_key = "task[{}]".format(key)
                    fill_pairs.append((fill_key, value))

        multiple_case_variants = prepare_template_data(fill_pairs)
        fill_data.update(multiple_case_variants)
        message = ''
        try:
            message = self._escape_missing_keys(message_templ, fill_data).\
                format(**fill_data)
        except Exception:
            # shouldn't happen
            self.log.warning(
                "Some keys are missing in {}".format(message_templ),
                exc_info=True)

        return message

    def _get_thumbnail_path(self, instance):
        """Returns abs url for thumbnail if present in instance repres"""
        thumbnail_path = None
        for repre in instance.data.get("representations", []):
            if repre.get('thumbnail') or "thumbnail" in repre.get('tags', []):
                repre_thumbnail_path = get_publish_repre_path(
                    instance, repre, False
                )
                if os.path.exists(repre_thumbnail_path):
                    thumbnail_path = repre_thumbnail_path
                break
        return thumbnail_path

    def _get_review_path(self, instance):
        """Returns abs url for review if present in instance repres"""
        review_path = None
        for repre in instance.data.get("representations", []):
            tags = repre.get('tags', [])
            if (repre.get("review")
                    or "review" in tags
                    or "burnin" in tags):
                repre_review_path = get_publish_repre_path(
                    instance, repre, False
                )
                if repre_review_path and os.path.exists(repre_review_path):
                    review_path = repre_review_path
                if "burnin" in tags:  # burnin has precedence if exists
                    break
        return review_path

    def _get_user_id(self, users, user_name):
        """Returns internal slack id for user name"""
        user_id = None
        user_name_lower = user_name.lower()
        for user in users:
            if (not user.get("deleted") and
                    (user_name_lower == user["name"].lower() or
                     # bots dont have display_name
                     user_name_lower == user["profile"].get("display_name",
                                                            '').lower() or
                     user_name_lower == user["profile"].get("real_name",
                                                            '').lower())):
                user_id = user["id"]
                break
        return user_id

    def _get_group_id(self, groups, group_name):
        """Returns internal group id for string name"""
        group_id = None
        for group in groups:
            if (not group.get("date_delete") and
                    (group_name.lower() == group["name"].lower() or
                     group_name.lower() == group["handle"])):
                group_id = group["id"]
                break
        return group_id

    def _translate_users(self, message, users, groups):
        """Replace all occurences of @mentions with proper <@name> format."""
        matches = re.findall(r"(?<!<)@\S+", message)
        in_quotes = re.findall(r"(?<!<)(['\"])(@[^'\"]+)", message)
        for item in in_quotes:
            matches.append(item[1])
        if not matches:
            return message

        for orig_user in matches:
            user_name = orig_user.replace("@", '')
            slack_id = self._get_user_id(users, user_name)
            mention = None
            if slack_id:
                mention = "<@{}>".format(slack_id)
            else:
                slack_id = self._get_group_id(groups, user_name)
                if slack_id:
                    mention = "<!subteam^{}>".format(slack_id)
            if mention:
                message = message.replace(orig_user, mention)

        return message

    def _escape_missing_keys(self, message, fill_data):
        """Double escapes placeholder which are missing in 'fill_data'"""
        placeholder_keys = re.findall(r"\{([^}]+)\}", message)

        fill_keys = []
        for key, value in fill_data.items():
            fill_keys.append(key)
            if isinstance(value, dict):
                for child_key in value.keys():
                    fill_keys.append("{}[{}]".format(key, child_key))

        not_matched = set(placeholder_keys) - set(fill_keys)

        for not_matched_item in not_matched:
            message = message.replace("{}".format(not_matched_item),
                                      "{{{}}}".format(not_matched_item))

        return message


@six.add_metaclass(ABCMeta)
class AbstractSlackOperations:

    @abstractmethod
    def _get_users_list(self):
        """Return response with user list, different methods Python 2 vs 3"""
        raise NotImplementedError

    @abstractmethod
    def _get_usergroups_list(self):
        """Return response with user list, different methods Python 2 vs 3"""
        raise NotImplementedError

    @abstractmethod
    def get_users_and_groups(self):
        """Return users and groups, different retry in Python 2 vs 3"""
        raise NotImplementedError

    @abstractmethod
    def send_message(self, channel, message, publish_files):
        """Sends message to channel, different methods in Python 2 vs 3"""
        pass

    def _get_users(self):
        """Parse users.list response into list of users (dicts)"""
        first = True
        next_page = None
        users = []
        while first or next_page:
            response = self._get_users_list()
            first = False
            next_page = response.get("response_metadata").get("next_cursor")
            for user in response.get("members"):
                users.append(user)

        return users

    def _get_groups(self):
        """Parses usergroups.list response into list of groups (dicts)"""
        response = self._get_usergroups_list()
        groups = []
        for group in response.get("usergroups"):
            groups.append(group)
        return groups

    def _enrich_error(self, error_str, channel):
        """Enhance known errors with more helpful notations."""
        if 'not_in_channel' in error_str:
            # there is no file.write.public scope, app must be explicitly in
            # the channel
            msg = " - application must added to channel '{}'.".format(channel)
            error_str += msg + " Ask Slack admin."
        return error_str


class SlackPython3Operations(AbstractSlackOperations):

    def __init__(self, token, log):
        from slack_sdk import WebClient

        self.client = WebClient(token=token)
        self.log = log

    def _get_users_list(self):
        return self.client.users_list()

    def _get_usergroups_list(self):
        return self.client.usergroups_list()

    def get_users_and_groups(self):
        from slack_sdk.errors import SlackApiError
        while True:
            try:
                users = self._get_users()
                groups = self._get_groups()
                break
            except SlackApiError as e:
                retry_after = e.response.headers.get("Retry-After")
                if retry_after:
                    print(
                        "Rate limit hit, sleeping for {}".format(retry_after))
                    time.sleep(int(retry_after))
                else:
                    self.log.warning("Cannot pull user info, "
                                     "mentions won't work", exc_info=True)
                    return [], []
            except Exception:
                self.log.warning("Cannot pull user info, "
                                 "mentions won't work", exc_info=True)
                return [], []

        return users, groups

    def send_message(self, channel, message, publish_files):
        from slack_sdk.errors import SlackApiError
        try:
            attachment_str = "\n\n Attachment links: \n"
            file_ids = []
            for published_file in publish_files:
                response = self.client.files_upload(
                    file=published_file,
                    filename=os.path.basename(published_file))
                attachment_str += "\n<{}|{}>".format(
                    response["file"]["permalink"],
                    os.path.basename(published_file))
                file_ids.append(response["file"]["id"])

            if publish_files:
                message += attachment_str

            response = self.client.chat_postMessage(
                channel=channel,
                text=message
            )
            return response.data["ts"], file_ids
        except SlackApiError as e:
            # # You will get a SlackApiError if "ok" is False
            if e.response.get("error"):
                error_str = self._enrich_error(str(e.response["error"]), channel)
            else:
                error_str = self._enrich_error(str(e), channel)
            self.log.warning("Error happened {}".format(error_str),
                             exc_info=True)
        except Exception as e:
            error_str = self._enrich_error(str(e), channel)
            self.log.warning("Not SlackAPI error", exc_info=True)

        return None, []


class SlackPython2Operations(AbstractSlackOperations):

    def __init__(self, token, log):
        from slackclient import SlackClient

        self.client = SlackClient(token=token)
        self.log = log

    def _get_users_list(self):
        return self.client.api_call("users.list")

    def _get_usergroups_list(self):
        return self.client.api_call("usergroups.list")

    def get_users_and_groups(self):
        while True:
            try:
                users = self._get_users()
                groups = self._get_groups()
                break
            except Exception:
                self.log.warning("Cannot pull user info, "
                                 "mentions won't work", exc_info=True)
                return [], []

        return users, groups

    def send_message(self, channel, message, publish_files):
        try:
            attachment_str = "\n\n Attachment links: \n"
            file_ids = []
            for p_file in publish_files:
                with open(p_file, 'rb') as pf:
                    response = self.client.api_call(
                        "files.upload",
                        file=pf,
                        channel=channel,
                        title=os.path.basename(p_file)
                    )
                    if response.get("error"):
                        error_str = self._enrich_error(
                            str(response.get("error")),
                            channel)
                        self.log.warning(
                            "Error happened: {}".format(error_str))
                    else:
                        attachment_str += "\n<{}|{}>".format(
                            response["file"]["permalink"],
                            os.path.basename(p_file))
                        file_ids.append(response["file"]["id"])

            if publish_files:
                message += attachment_str

            response = self.client.api_call(
                "chat.postMessage",
                channel=channel,
                text=message
            )
            if response.get("error"):
                error_str = self._enrich_error(str(response.get("error")),
                                               channel)
                self.log.warning("Error happened: {}".format(error_str),
                                 exc_info=True)
            else:
                return response["ts"], file_ids
        except Exception as e:
            # You will get a SlackApiError if "ok" is False
            error_str = self._enrich_error(str(e), channel)
            self.log.warning("Error happened: {}".format(error_str),
                             exc_info=True)

        return None, []
