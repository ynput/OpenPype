import pyblish.api
import openpype.api
import openpype.hosts.maya.api.action

import os

COLOUR_SPACES = ['sRGB']
MIPMAP_EXTENSIONS = ['tdl']


class ValidateMvLookContents(pyblish.api.InstancePlugin):
    order = openpype.api.ValidateContentsOrder
    families = ['mvLook']
    hosts = ['maya']
    label = 'Validate mvLook Data'
    actions = [openpype.hosts.maya.api.action.SelectInvalidAction]

    # Allow this validation step to be skipped when you just need to
    # get things pushed through.
    optional = True

    # These intents get enforced checks, other ones get warnings.
    enforced_intents = ['-', 'Final']

    def process(self, instance):
        intent = instance.context.data['intent']['value']
        expectMipMap = instance.data["expectMipMap"]
        enforced = True
        if intent in self.enforced_intents:
            self.log.info("This validation will be enforced: '{}'"
                          .format(intent))
        else:
            enforced = False
            self.log.info("This validation will NOT be enforced: '{}'"
                          .format(intent))

        if not instance[:]:
            raise RuntimeError("Instance is empty")

        invalid = set()

        resources = instance.data.get("resources", [])
        for resource in resources:
            files = resource["files"]
            self.log.debug("Resouce '{}', files: [{}]".format(resource, files))
            node = resource["node"]
            if len(files) == 0:
                self.log.error("File node '{}' uses no or non-existing "
                               "files".format(node))
                invalid.add(node)
                continue
            for fname in files:
                if not self.valid_file(fname):
                    self.log.error("File node '{}'/'{}' is not valid"
                                   .format(node, fname))
                    invalid.add(node)

                if expectMipMap and not self.is_or_has_mipmap(fname, files):
                    msg = "File node '{}'/'{}' does not have a mipmap".format(
                        node, fname)
                    if enforced:
                        invalid.add(node)
                        self.log.error(msg)
                        raise RuntimeError(msg)
                    else:
                        self.log.warning(msg)

        if invalid:
            raise RuntimeError("'{}' has invalid look "
                               "content".format(instance.name))

    def valid_file(self, fname):
        self.log.debug("Checking validity of '{}'".format(fname))
        if not os.path.exists(fname):
            return False
        if os.path.getsize(fname) == 0:
            return False
        return True

    def is_or_has_mipmap(self, fname, files):
        ext = os.path.splitext(fname)[1][1:]
        if ext in MIPMAP_EXTENSIONS:
            self.log.debug("Is a mipmap '{}'".format(fname))
            return True

        for colour_space in COLOUR_SPACES:
            for mipmap_ext in MIPMAP_EXTENSIONS:
                mipmap_fname = '.'.join([fname, colour_space, mipmap_ext])
                if mipmap_fname in files:
                    self.log.debug("Has a mipmap '{}'".format(fname))
                    return True
        return False
