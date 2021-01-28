from maya import cmds
import pyblish.api
import pype.api
import pype.hosts.maya.action
import re


class ValidateModelName(pyblish.api.InstancePlugin):
    """Validate name of model

    starts with (somename)_###_(materialID)_GEO
    materialID must be present in list
    padding number doesn't have limit

    """
    optional = True
    order = pype.api.ValidateContentsOrder
    hosts = ["maya"]
    families = ["model"]
    label = "Model Name"
    actions = [pype.hosts.maya.action.SelectInvalidAction]
    # path to shader names definitions
    # TODO: move it to preset file
    material_file = None
    active = False
    regex = '(.*)_(\\d)*_(.*)_(GEO)'

    @classmethod
    def get_invalid(cls, instance):

        # find out if supplied transform is group or not
        def is_group(groupName):
            try:
                children = cmds.listRelatives(groupName, children=True)
                for child in children:
                    if not cmds.ls(child, transforms=True):
                        return False
                return True
            except:
                return False

        invalid = []
        content_instance = instance.data.get("setMembers", None)
        if not content_instance:
            cls.log.error("Instance has no nodes!")
            return True
        pass
        descendants = cmds.listRelatives(content_instance,
                                         allDescendents=True,
                                         fullPath=True) or []

        descendants = cmds.ls(descendants, noIntermediate=True, long=True)
        trns = cmds.ls(descendants, long=False, type=('transform'))

        # filter out groups
        filter = [node for node in trns if not is_group(node)]

        # load shader list file as utf-8
        if cls.material_file:
            shader_file = open(cls.material_file, "r")
            shaders = shader_file.readlines()
            shader_file.close()

        # strip line endings from list
        shaders = map(lambda s: s.rstrip(), shaders)

        # compile regex for testing names
        r = re.compile(cls.regex)

        for obj in filter:
            m = r.match(obj)
            if m is None:
                cls.log.error("invalid name on: {}".format(obj))
                invalid.append(obj)
            else:
                # if we have shader files and shader named group is in
                # regex, test this group against names in shader file
                if 'shader' in r.groupindex and shaders:
                    try:
                        if not m.group('shader') in shaders:
                            cls.log.error(
                                "invalid materialID on: {0} ({1})".format(
                                    obj, m.group('shader')))
                            invalid.append(obj)
                    except IndexError:
                        # shader named group doesn't match
                        cls.log.error(
                            "shader group doesn't match: {}".format(obj))
                        invalid.append(obj)

        return invalid

    def process(self, instance):

        invalid = self.get_invalid(instance)

        if invalid:
            raise RuntimeError("Model naming is invalid. See log.")
