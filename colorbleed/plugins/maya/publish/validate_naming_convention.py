import re

import pyblish.api
import colorbleed.api


class ValidateNamingConvention(pyblish.api.InstancePlugin):

    label = ""
    host = ["maya"]
    actions = [colorbleed.api.SelectInvalidAction]

    @staticmethod
    def get_invalid(instance):

        invalid = []
        # todo: change pattern to company standard
        pattern = re.compile("[a-zA-Z]+_[A-Z]{3}")

        nodes = list(instance)
        for node in nodes:
            match = pattern.match(node)
            if not match:
                invalid.append(node)

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            self.log.error("Found invalid naming convention. Failed noted :\n"
                           "%s" % invalid)
