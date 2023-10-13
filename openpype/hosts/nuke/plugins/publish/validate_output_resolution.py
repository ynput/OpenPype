import pyblish.api

from openpype.hosts.nuke import api as napi
from openpype.pipeline.publish import RepairAction
from openpype.pipeline import (
    PublishXmlValidationError,
    OptionalPyblishPluginMixin
)

import nuke


class ValidateOutputResolution(
    OptionalPyblishPluginMixin,
    pyblish.api.InstancePlugin
):
    """Validates Output Resolution.

    It is making sure the resolution of write's input is the same as
    Format definition of script in Root node.
    """

    order = pyblish.api.ValidatorOrder
    optional = True
    families = ["render"]
    label = "Validate Write resolution"
    hosts = ["nuke"]
    actions = [RepairAction]

    missing_msg = "Missing Reformat node in render group node"
    resolution_msg = "Reformat is set to wrong format"

    def process(self, instance):
        if not self.is_active(instance.data):
            return

        invalid = self.get_invalid(instance)
        if invalid:
            raise PublishXmlValidationError(self, invalid)

    @classmethod
    def get_reformat(cls, instance):
        child_nodes = (
            instance.data.get("transientData", {}).get("childNodes")
            or instance
        )

        reformat = None
        for inode in child_nodes:
            if inode.Class() != "Reformat":
                continue
            reformat = inode

        return reformat

    @classmethod
    def get_invalid(cls, instance):
        def _check_resolution(instance, reformat):
            root_width = instance.data["resolutionWidth"]
            root_height = instance.data["resolutionHeight"]

            write_width = reformat.format().width()
            write_height = reformat.format().height()

            if (root_width != write_width) or (root_height != write_height):
                return None
            else:
                return True

        # check if reformat is in render node
        reformat = cls.get_reformat(instance)
        if not reformat:
            return cls.missing_msg

        # check if reformat is set to correct root format
        correct_format = _check_resolution(instance, reformat)
        if not correct_format:
            return cls.resolution_msg

    @classmethod
    def repair(cls, instance):
        child_nodes = (
            instance.data.get("transientData", {}).get("childNodes")
            or instance
        )

        invalid = cls.get_invalid(instance)
        grp_node = instance.data["transientData"]["node"]

        if cls.missing_msg == invalid:
            # make sure we are inside of the group node
            with grp_node:
                # find input node and select it
                _input = None
                for inode in child_nodes:
                    if inode.Class() != "Input":
                        continue
                    _input = inode

                # add reformat node under it
                with napi.maintained_selection():
                    _input['selected'].setValue(True)
                    _rfn = nuke.createNode("Reformat", "name Reformat01")
                    _rfn["resize"].setValue(0)
                    _rfn["black_outside"].setValue(1)

                cls.log.info("Adding reformat node")

        if cls.resolution_msg == invalid:
            reformat = cls.get_reformat(instance)
            reformat["format"].setValue(nuke.root()["format"].value())
            cls.log.info("Fixing reformat to root.format")
