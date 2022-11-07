# -*- coding: utf-8 -*-
import os
import re

import pyblish.api


class CollectKitsuUsername(pyblish.api.ContextPlugin):
    """Collect Kitsu username from the kitsu login"""

    order = pyblish.api.CollectorOrder + 0.499
    label = "Kitsu username"

    def process(self, context):
        for instance in context:
            kitsu_login = os.environ['KITSU_LOGIN']

            if kitsu_login:
                kitsu_username = kitsu_login.split("@")[0]
                kitsu_username = kitsu_username.split('.')
                kitsu_username = ' '.join(kitsu_username)

                new_username = re.sub('[^a-zA-Z]', ' ', kitsu_username)

                instance.data['customData'] = {
                    "kitsuUsername": new_username.title()
                }
