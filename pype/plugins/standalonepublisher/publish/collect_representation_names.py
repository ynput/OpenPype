"""
Requires:
    Nothing

Provides:
    Instance
"""

import pyblish.api
from pprint import pformat
import re
import os

class CollecRepresentationNames(pyblish.api.InstancePlugin):
    """
    Sets the representation names for given families based on RegEx filter
    """

    label = "Collect Representaion Names"
    order = pyblish.api.CollectorOrder
    families = []
    hosts = ["standalonepublisher"]
    name_filter = ""

    def process(self, instance):
        self.log.debug(f"instance.data: {pformat(instance.data['representations'])}")
        for repre in instance.data['representations']:
            self.log.debug(repre['files'])
            if isinstance(repre['files'], list):
                shortened_name = os.path.splitext(repre['files'][0])[0]
                new_repre_name = re.search(self.name_filter, shortened_name)
            else:
                new_repre_name = re.search(self.name_filter, repre['files'])


            self.log.debug(new_repre_name.group())
            repre['name'] = new_repre_name.group()
            repre['outputName'] = new_repre_name.group()

        self.log.debug(f"instance.data: {pformat(instance.data['representations'])}")
