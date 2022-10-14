from pprint import pformat
import pyblish.api

from openpype.pipeline import PublishXmlValidationError
from openpype.pipeline.publish import RepairAction
from openpype.hosts.nuke.api.lib import (
    get_avalon_knob_data,
    WorkfileSettings
)
import nuke


class ValidateScriptAttributes(pyblish.api.InstancePlugin):
    """ Validates file output. """

    order = pyblish.api.ValidatorOrder + 0.1
    families = ["workfile"]
    label = "Validatte script attributes"
    hosts = ["nuke"]
    optional = True
    actions = [RepairAction]

    def process(self, instance):
        root = nuke.root()
        knob_data = get_avalon_knob_data(root)
        asset = instance.data["assetEntity"]
        # get asset data frame values
        frame_start = asset["data"]["frameStart"]
        frame_end = asset["data"]["frameEnd"]
        handle_start = asset["data"]["handleStart"]
        handle_end = asset["data"]["handleEnd"]

        # These attributes will be checked
        attributes = [
            "fps",
            "frameStart",
            "frameEnd",
            "resolutionWidth",
            "resolutionHeight",
            "handleStart",
            "handleEnd"
        ]

        # get only defined attributes from asset data
        asset_attributes = {
            attr: asset["data"][attr]
            for attr in attributes
            if attr in asset["data"]
        }
        # fix float to max 4 digints (only for evaluating)
        fps_data = float("{0:.4f}".format(
            asset_attributes["fps"]))
        # fix frame values to include handles
        asset_attributes.update({
            "frameStart": frame_start - handle_start,
            "frameEnd": frame_end + handle_end,
            "fps": fps_data
        })

        self.log.debug(pformat(
            asset_attributes
        ))

        # Get format
        _format = root["format"].value()

        # Get values from nukescript
        script_attributes = {
            "handleStart": int(knob_data["handleStart"]),
            "handleEnd": int(knob_data["handleEnd"]),
            "fps": float("{0:.4f}".format(root['fps'].value())),
            "frameStart": int(root["first_frame"].getValue()),
            "frameEnd": int(root["last_frame"].getValue()),
            "resolutionWidth": _format.width(),
            "resolutionHeight": _format.height(),
            "pixelAspect": _format.pixelAspect()
        }
        self.log.debug(pformat(
            script_attributes
        ))

        # Compare asset's values Nukescript X Database
        not_matching = []
        for attr in attributes:
            self.log.debug(
                "Asset vs Script attribute \"{}\": {}, {}".format(
                    attr,
                    asset_attributes[attr],
                    script_attributes[attr]
                )
            )
            if asset_attributes[attr] != script_attributes[attr]:
                not_matching.append({
                    "name": attr,
                    "expected": asset_attributes[attr],
                    "actual": script_attributes[attr]
                })

        # Raise error if not matching
        if not_matching:
            msg = "Following attributes are not set correctly: \n{}"
            attrs_wrong_str = "\n".join([
                (
                    "`{0}` is set to `{1}`, "
                    "but should be set to `{2}`"
                ).format(at["name"], at["actual"], at["expected"])
                for at in not_matching
            ])
            attrs_wrong_html = "<br/>".join([
                (
                    "-- __{0}__ is set to __{1}__, "
                    "but should be set to __{2}__"
                ).format(at["name"], at["actual"], at["expected"])
                for at in not_matching
            ])
            raise PublishXmlValidationError(
                self, msg.format(attrs_wrong_str),
                formatting_data={
                    "failed_attributes": attrs_wrong_html
                }
            )

    @classmethod
    def repair(cls, instance):
        cls.log.debug("__ repairing instance: {}".format(instance))
        WorkfileSettings().set_context_settings()
