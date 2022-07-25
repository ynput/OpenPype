from pprint import pformat
import pyblish.api

from openpype.client import get_project, get_asset_by_id, get_asset_by_name
from openpype.pipeline import legacy_io
from openpype.pipeline import PublishXmlValidationError
import nuke


@pyblish.api.log
class ValidateScriptAttributes(pyblish.api.InstancePlugin):
    """ Validates file output. """

    order = pyblish.api.ValidatorOrder + 0.1
    families = ["workfile"]
    label = "Validatte script attributes"
    hosts = ["nuke"]
    optional = True

    def process(self, instance):
        ctx_data = instance.context.data
        project_name = legacy_io.active_project()
        asset_name = ctx_data["asset"]
        asset = get_asset_by_name(project_name, asset_name)
        asset_data = asset["data"]

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

        asset_attributes = {
            attr: asset_data[attr]
            for attr in attributes
            if attr in asset_data
        }

        self.log.debug(pformat(
            asset_attributes
        ))

        handle_start = asset_attributes["handleStart"]
        handle_end = asset_attributes["handleEnd"]
        asset_attributes["fps"] = float("{0:.4f}".format(
            asset_attributes["fps"]))

        root = nuke.root()
        # Get values from nukescript
        script_attributes = {
            "handleStart": ctx_data["handleStart"],
            "handleEnd": ctx_data["handleEnd"],
            "fps": float("{0:.4f}".format(ctx_data["fps"])),
            "frameStart": int(root["first_frame"].getValue()),
            "frameEnd": int(root["last_frame"].getValue()),
            "resolutionWidth": ctx_data["resolutionWidth"],
            "resolutionHeight": ctx_data["resolutionHeight"],
            "pixelAspect": ctx_data["pixelAspect"]
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
            msg = "Attributes '{}' are not set correctly"
            # Alert user that handles are set if Frame start/end not match
            message = msg.format(", ".join(
                [at["name"] for at in not_matching]))
            raise PublishXmlValidationError(
                self, message,
                formatting_data={
                    "missing_attributes": not_matching
                }
            )

    def check_parent_hierarchical(
        self, project_name, parent_type, parent_id, attr
    ):
        if parent_id is None:
            return None

        doc = None
        if parent_type == "project":
            doc = get_project(project_name)
        elif parent_type == "asset":
            doc = get_asset_by_id(project_name, parent_id)

        if not doc:
            return None

        doc_data = doc["data"]
        if attr in doc_data:
            self.log.info(attr)
            return doc_data[attr]

        if parent_type == "project":
            return None

        parent_id = doc_data.get("visualParent")
        new_parent_type = "asset"
        if parent_id is None:
            parent_id = doc["parent"]
            new_parent_type = "project"

        return self.check_parent_hierarchical(
            project_name, new_parent_type, parent_id, attr
        )
