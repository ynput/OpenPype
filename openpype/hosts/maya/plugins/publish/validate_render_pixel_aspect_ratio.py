from maya import cmds

import pyblish.api
import openpype.api


class ValidateRenderResolution(pyblish.api.InstancePlugin):
    """Validates Render Resolution and Pixel Aspect Ratio matches with asset"""

    order = openpype.api.ValidateContentsOrder
    label = "Resolution & Pixel Aspect Ratio"
    hosts = ["maya"]
    families = ["renderlayer"]
    actions = [openpype.api.RepairAction]

    def process(self, instance):

        asset = instance.data.get("assetEntity")

        required = ["pixelAspect"]
        optionals = ["resolutionWidth", "resolutionHeight"]

        for key in optionals:
            if not self._valid_key(instance, asset, key):
                self.log.warning("Optional value mismatch '{}': {} "
                                 "(expected: {})".format(key,
                                                         instance.data[key],
                                                         asset["data"][key]))

        invalid = False
        for key in required:
            if not self._valid_key(instance, asset, key):
                self.log.error("Required value mismatch '{}':  {} "
                               "(must be: {})".format(key,
                                                      instance.data[key],
                                                      asset["data"][key]))
                invalid = True

        if invalid:
            raise RuntimeError("Invalid resolution or pixel aspect ratio.")

    @staticmethod
    def _valid_key(instance, asset, key):
        if key in asset["data"] and key in instance.data:
            if asset["data"][key] != instance.data[key]:
                return False
        return True

    @classmethod
    def repair(cls, instance):

        asset = instance.data.get("assetEntity")
        keys = [
            # Disabled for now since these are optional
            # ("resolutionWidth", "defaultResolution.resolutionWidth"),
            # ("resolutionHeight", "defaultResolution.resolutionHeight"),
            ("pixelAspect", "defaultResolution.pixelAspect")
        ]

        for key, attr in keys:
            if not cls._valid_key(instance, asset, key):
                value = asset["data"][key]
                print("Setting {}: {}".format(attr, value))

                if key == "pixelAspect":
                    # Special behavior for pixel aspect
                    x = cmds.getAttr("defaultResolution.width")
                    y = cmds.getAttr("defaultResolution.height")
                    device_aspect = value * (x / y)
                    print("Setting defaultResolution.deviceAspectRatio: "
                          "{}".format(device_aspect))
                    cmds.setAttr("defaultResolution.deviceAspectRatio",
                                 device_aspect)
                    cmds.setAttr("defaultResolution.pixelAspect", value)
                    continue

                cmds.setAttr(attr, value)


