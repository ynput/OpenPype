"""Loads publishing context from json and continues in publish process.

Requires:
    anatomy -> context["anatomy"] *(pyblish.api.CollectorOrder - 0.11)

Provides:
    context, instances -> All data from previous publishing process.
"""

import ftrack_api
import os

import pyblish.api


class CollectUsername(pyblish.api.ContextPlugin):
    """
        Translates user email to Ftrack username.

        Emails in Ftrack are same as company's Slack, username is needed to
        load data to Ftrack.

        Expects "pype.club" user created on Ftrack and FTRACK_BOT_API_KEY env
        var set up.

    """
    order = pyblish.api.CollectorOrder - 0.488
    label = "Collect ftrack username"
    hosts = ["webpublisher", "photoshop"]
    targets = ["remotepublish", "filespublish"]

    _context = None

    def process(self, context):
        self.log.info("CollectUsername")

        os.environ["FTRACK_API_USER"] = os.environ["FTRACK_BOT_API_USER"]
        os.environ["FTRACK_API_KEY"] = os.environ["FTRACK_BOT_API_KEY"]

        for instance in context:
            email = instance.data["user_email"]
            self.log.info("email:: {}".format(email))
            session = ftrack_api.Session(auto_connect_event_hub=False)
            user = session.query("User where email like '{}'".format(
                email))

            if not user:
                raise ValueError(
                    "Couldnt find user with {} email".format(email))

            os.environ["FTRACK_API_USER"] = user[0].get("username")
            break
