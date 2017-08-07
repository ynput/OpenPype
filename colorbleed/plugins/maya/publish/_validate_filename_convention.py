import re
import os

import maya.cmds as cmds

import pyblish.api
import colorbleed.api


class ValidateFileNameConvention(pyblish.api.InstancePlugin):

    label = ""
    families = ["colorbleed.lookdev"]
    host = ["maya"]
    optional = True

    order = pyblish.api.ValidatorOrder
    actions = [colorbleed.api.SelectInvalidAction]

    @staticmethod
    def get_invalid(instance):

        invalid = []
        # todo: change pattern to company standard
        pattern = re.compile("[a-zA-Z]+_[A-Z]{3}")

        nodes = cmds.ls(instance, type="file")
        for node in nodes:
            # get texture path
            texture = cmds.getAttr("{}.fileTextureName".format(node))
            if not texture:
                self.log.error("")
                invalid.append(node)
            filename = os.path.split(os.path.basename(texture))[0]
            match = pattern.match(filename)
            if not match:
                invalid.append(node)

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)
        if invalid:
            self.log.error("Found invalid naming convention. Failed noted :\n"
                           "%s" % invalid)
