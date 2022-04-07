import os

import gazu

import pyblish.api


class CollectKitsuSession(pyblish.api.ContextPlugin):
    """Collect Kitsu session using user credentials"""

    order = pyblish.api.CollectorOrder
    label = "Kitsu user session"


    def process(self, context):

        gazu.client.set_host(os.environ["KITSU_SERVER"])
        gazu.log_in(os.environ["KITSU_LOGIN"], os.environ["KITSU_PWD"])