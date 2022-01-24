import re
import os
import pyblish.api


class CollectRepresentationNames(pyblish.api.InstancePlugin):
    """
    Sets the representation names for given families based on RegEx filter
    """

    label = "Collect Representation Names"
    order = pyblish.api.CollectorOrder
    families = []
    hosts = ["standalonepublisher"]
    name_filter = ""

    def process(self, instance):
        for repre in instance.data['representations']:
            new_repre_name = None
            if isinstance(repre['files'], list):
                shortened_name = os.path.splitext(repre['files'][0])[0]
                new_repre_name = re.search(self.name_filter,
                                           shortened_name).group()
            else:
                new_repre_name = re.search(self.name_filter,
                                           repre['files']).group()

            if new_repre_name:
                repre['name'] = new_repre_name

            repre['outputName'] = repre['name']
