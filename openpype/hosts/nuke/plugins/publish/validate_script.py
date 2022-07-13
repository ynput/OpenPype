import pyblish.api

from openpype.client import get_project, get_asset_by_id
from openpype import lib
from openpype.pipeline import legacy_io


@pyblish.api.log
class ValidateScript(pyblish.api.InstancePlugin):
    """ Validates file output. """

    order = pyblish.api.ValidatorOrder + 0.1
    families = ["workfile"]
    label = "Check script settings"
    hosts = ["nuke"]
    optional = True

    def process(self, instance):
        ctx_data = instance.context.data
        asset_name = ctx_data["asset"]
        asset = lib.get_asset(asset_name)
        asset_data = asset["data"]
        project_name = legacy_io.active_project()

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

        # Value of these attributes can be found on parents
        hierarchical_attributes = [
            "fps",
            "resolutionWidth",
            "resolutionHeight",
            "pixelAspect",
            "handleStart",
            "handleEnd"
        ]

        missing_attributes = []
        asset_attributes = {}
        for attr in attributes:
            if attr in asset_data:
                asset_attributes[attr] = asset_data[attr]

            elif attr in hierarchical_attributes:
                # TODO this should be probably removed
                #   Hierarchical attributes is not a thing since Pype 2?

                # Try to find attribute on parent
                parent_id = asset['parent']
                parent_type = "project"
                if asset_data['visualParent'] is not None:
                    parent_type = "asset"
                    parent_id = asset_data['visualParent']

                value = self.check_parent_hierarchical(
                    project_name, parent_type, parent_id, attr
                )
                if value is None:
                    missing_attributes.append(attr)
                else:
                    asset_attributes[attr] = value
            else:
                missing_attributes.append(attr)

        # Raise error if attributes weren't found on asset in database
        if len(missing_attributes) > 0:
            atr = ", ".join(missing_attributes)
            msg = 'Missing attributes "{}" in asset "{}"'
            message = msg.format(atr, asset_name)
            raise ValueError(message)

        # Get handles from database, Default is 0 (if not found)
        handle_start = 0
        handle_end = 0
        if "handleStart" in asset_attributes:
            handle_start = asset_attributes["handleStart"]
        if "handleEnd" in asset_attributes:
            handle_end = asset_attributes["handleEnd"]

        asset_attributes["fps"] = float("{0:.4f}".format(
                asset_attributes["fps"]))

        # Get values from nukescript
        script_attributes = {
            "handleStart": ctx_data["handleStart"],
            "handleEnd": ctx_data["handleEnd"],
            "fps": float("{0:.4f}".format(ctx_data["fps"])),
            "frameStart": ctx_data["frameStart"],
            "frameEnd": ctx_data["frameEnd"],
            "resolutionWidth": ctx_data["resolutionWidth"],
            "resolutionHeight": ctx_data["resolutionHeight"],
            "pixelAspect": ctx_data["pixelAspect"]
        }

        # Compare asset's values Nukescript X Database
        not_matching = []
        for attr in attributes:
            self.log.debug("asset vs script attribute \"{}\": {}, {}".format(
                attr, asset_attributes[attr], script_attributes[attr])
            )
            if asset_attributes[attr] != script_attributes[attr]:
                not_matching.append(attr)

        # Raise error if not matching
        if len(not_matching) > 0:
            msg = "Attributes '{}' are not set correctly"
            # Alert user that handles are set if Frame start/end not match
            if (
                (("frameStart" in not_matching) or ("frameEnd" in not_matching)) and
                ((handle_start > 0) or (handle_end > 0))
            ):
                msg += " (`handle_start` are set to {})".format(handle_start)
                msg += " (`handle_end` are set to {})".format(handle_end)
            message = msg.format(", ".join(not_matching))
            raise ValueError(message)

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
