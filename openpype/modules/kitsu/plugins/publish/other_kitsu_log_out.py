# -*- coding: utf-8 -*-
import gazu
import pyblish.api


class KitsuLogOut(pyblish.api.ContextPlugin):
    """
    Log out from Kitsu API
    """

    order = pyblish.api.IntegratorOrder + 10
    label = "Kitsu Log Out"

    def process(self, context):
        gazu.log_out()
