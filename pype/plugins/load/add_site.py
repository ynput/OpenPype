import os

from avalon import api


class AddSyncSite(api.Loader):
    """Add sync site to representation"""
    representations = ["*"]
    families = ["*"]

    label = "Add Sync Site"
    order = 20
    icon = "download"
    color = "#999999"

    def load(self, context, name=None, namespace=None, data=None):
        self.log.info("Added site to representation: {0}".format(self.fname))
        self.add_site_to_representation(self.fname)

    @staticmethod
    def add_site_to_representation(path):
        pass
