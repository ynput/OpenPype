# from pype import plugins
import os
import json
import re
import copy
import pyblish.api
import tempfile
from avalon import io, api


class ExtractVideoTracksLuts(pyblish.api.InstancePlugin):
    """Collect video tracks effects into context."""

    order = pyblish.api.ExtractorOrder
    label = "Export Soft Lut Effects"
    families = ["lut"]

    def process(self, instance):
        item = instance.data["item"]
        effects = instance.data.get("effectTrackItems")

        instance.data["families"] = [f for f in instance.data.get(
            "families", []) if f not in ["lut"]]

        self.log.debug(
            "__ instance.data[families]: `{}`".format(
                instance.data["families"]))

        # skip any without effects
        if not effects:
            return

        subset = instance.data.get("subset")
        subset_split = re.findall(r'[A-Z][^A-Z]*', subset)

        if len(subset_split) > 0:
            root_name = subset.replace(subset_split[0], "")
            subset_split.insert(0, root_name.capitalize())

        subset_split.insert(0, "lut")

        self.log.debug("creating staging dir")
        # staging_dir = self.staging_dir(instance)

        # TODO: only provisory will be replace by function
        staging_dir = instance.data.get('stagingDir', None)

        if not staging_dir:
            staging_dir = os.path.normpath(
                tempfile.mkdtemp(prefix="pyblish_tmp_")
            )
            instance.data['stagingDir'] = staging_dir

        self.log.debug("creating staging dir: `{}`".format(staging_dir))

        transfers = list()
        if "transfers" not in instance.data:
            instance.data["transfers"] = list()

        name = "".join(subset_split)
        ext = "json"
        file = name + "." + ext

        # create new instance and inherit data
        data = {}
        for key, value in instance.data.iteritems():
            data[key] = value

        # change names
        data["subset"] = name
        data["family"] = "lut"
        data["families"] = []
        data["name"] = data["subset"] + "_" + data["asset"]
        data["label"] = "{} - {} - ({})".format(
            data['asset'], data["subset"], os.path.splitext(file)[1]
        )
        data["source"] = data["sourcePath"]

        # WARNING instance should not be created in Extractor!
        # create new instance
        instance = instance.context.create_instance(**data)
        # TODO replace line below with `instance.data["resourcesDir"]`
        # when instance is created during collection part
        dst_dir = self.resource_destination_dir(instance)

        # change paths in effects to files
        for k, effect in effects["effects"].items():
            trn = self.copy_linked_files(effect, dst_dir)
            if trn:
                transfers.append((trn[0], trn[1]))

        instance.data["transfers"].extend(transfers)
        self.log.debug("_ transfers: `{}`".format(
            instance.data["transfers"]))

        # create representations
        instance.data["representations"] = list()

        transfer_data = [
            "handleStart", "handleEnd", "sourceIn", "sourceOut",
            "frameStart", "frameEnd", "sourceInH", "sourceOutH",
            "clipIn", "clipOut", "clipInH", "clipOutH", "asset", "track",
            "version"
        ]

        # pass data to version
        version_data = dict()
        version_data.update({k: instance.data[k] for k in transfer_data})

        # add to data of representation
        version_data.update({
            "colorspace": item.sourceMediaColourTransform(),
            "colorspaceScript": instance.context.data["colorspace"],
            "families": ["plate", "lut"],
            "subset": name,
            "fps": instance.context.data["fps"]
        })
        instance.data["versionData"] = version_data

        representation = {
            'files': file,
            'stagingDir': staging_dir,
            'name': "lut" + ext.title(),
            'ext': ext
        }
        instance.data["representations"].append(representation)

        self.log.debug("_ representations: `{}`".format(
            instance.data["representations"]))

        self.log.debug("_ version_data: `{}`".format(
            instance.data["versionData"]))

        with open(os.path.join(staging_dir, file), "w") as outfile:
            outfile.write(json.dumps(effects, indent=4, sort_keys=True))

        return

    def copy_linked_files(self, effect, dst_dir):
        for k, v in effect["node"].items():
            if k in "file" and v != '':
                base_name = os.path.basename(v)
                dst = os.path.join(dst_dir, base_name).replace("\\", "/")

                # add it to the json
                effect["node"][k] = dst
                return (v, dst)

    def resource_destination_dir(self, instance):
        # WARNING this is from `collect_instance_anatomy_data.py`
        anatomy_data = copy.deepcopy(instance.context.data["anatomyData"])
        project_entity = instance.context.data["projectEntity"]
        context_asset_entity = instance.context.data["assetEntity"]

        asset_name = instance.data["asset"]
        if context_asset_entity["name"] == asset_name:
            asset_entity = context_asset_entity

        else:
            asset_entity = io.find_one({
                "type": "asset",
                "name": asset_name,
                "parent": project_entity["_id"]
            })

        subset_name = instance.data["subset"]
        version_number = instance.data.get("version")
        latest_version = None

        if asset_entity:
            subset_entity = io.find_one({
                "type": "subset",
                "name": subset_name,
                "parent": asset_entity["_id"]
            })

            if subset_entity is None:
                self.log.debug("Subset entity does not exist yet.")
            else:
                version_entity = io.find_one(
                    {
                        "type": "version",
                        "parent": subset_entity["_id"]
                    },
                    sort=[("name", -1)]
                )
                if version_entity:
                    latest_version = version_entity["name"]

        if version_number is None:
            version_number = 1
            if latest_version is not None:
                version_number += int(latest_version)

        anatomy_data.update({
            "asset": asset_name,
            "family": instance.data["family"],
            "subset": subset_name,
            "version": version_number,
            "hierarchy": instance.data["hierarchy"]
        })

        resolution_width = instance.data.get("resolutionWidth")
        if resolution_width:
            anatomy_data["resolution_width"] = resolution_width

        resolution_height = instance.data.get("resolutionHeight")
        if resolution_height:
            anatomy_data["resolution_height"] = resolution_height

        pixel_aspect = instance.data.get("pixelAspect")
        if pixel_aspect:
            anatomy_data["pixel_aspect"] = float("{:0.2f}".format(pixel_aspect))

        fps = instance.data.get("fps")
        if resolution_height:
            anatomy_data["fps"] = float("{:0.2f}".format(fps))

        instance.data["projectEntity"] = project_entity
        instance.data["assetEntity"] = asset_entity
        instance.data["anatomyData"] = anatomy_data
        instance.data["latestVersion"] = latest_version
        instance.data["version"] = version_number

        # WARNING this is from `collect_resources_path.py`
        anatomy = instance.context.data["anatomy"]

        template_data = copy.deepcopy(instance.data["anatomyData"])

        # This is for cases of Deprecated anatomy without `folder`
        # TODO remove when all clients have solved this issue
        template_data.update({
            "frame": "FRAME_TEMP",
            "representation": "TEMP"
        })

        anatomy_filled = anatomy.format(template_data)

        if "folder" in anatomy.templates["publish"]:
            publish_folder = anatomy_filled["publish"]["folder"]
        else:
            # solve deprecated situation when `folder` key is not underneath
            # `publish` anatomy
            project_name = api.Session["AVALON_PROJECT"]
            self.log.warning((
                "Deprecation warning: Anatomy does not have set `folder`"
                " key underneath `publish` (in global of for project `{}`)."
            ).format(project_name))

            file_path = anatomy_filled["publish"]["path"]
            # Directory
            publish_folder = os.path.dirname(file_path)

        publish_folder = os.path.normpath(publish_folder)
        resources_folder = os.path.join(publish_folder, "resources")

        instance.data["publishDir"] = publish_folder
        instance.data["resourcesDir"] = resources_folder

        return resources_folder
