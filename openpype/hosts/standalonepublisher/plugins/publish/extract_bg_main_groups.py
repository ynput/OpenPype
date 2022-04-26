import os
import copy
import json

import pyblish.api

import openpype.api
from openpype.pipeline import legacy_io

PSDImage = None


class ExtractBGMainGroups(openpype.api.Extractor):
    label = "Extract Background Layout"
    order = pyblish.api.ExtractorOrder + 0.02
    families = ["backgroundLayout"]
    hosts = ["standalonepublisher"]

    new_instance_family = "background"

    # Presetable
    allowed_group_names = [
        "OL", "BG", "MG", "FG", "UL", "SB", "SKY", "Field Guide", "Field_Guide",
        "ANIM"
    ]

    def process(self, instance):
        # Check if python module `psd_tools` is installed
        try:
            global PSDImage
            from psd_tools import PSDImage
        except Exception:
            raise AssertionError(
                "BUG: Python module `psd-tools` is not installed!"
            )

        self.allowed_group_names = [
            name.lower()
            for name in self.allowed_group_names
        ]
        repres = instance.data.get("representations")
        if not repres:
            self.log.info("There are no representations on instance.")
            return

        self.redo_global_plugins(instance)

        repres = instance.data.get("representations")
        if not repres:
            self.log.info("There are no representations on instance.")
            return

        if not instance.data.get("transfers"):
            instance.data["transfers"] = []

        # Prepare staging dir
        staging_dir = self.staging_dir(instance)
        if not os.path.exists(staging_dir):
            os.makedirs(staging_dir)

        # Prepare publish dir for transfers
        publish_dir = instance.data["publishDir"]

        for repre in tuple(repres):
            # Skip all files without .psd extension
            repre_ext = repre["ext"].lower()
            if repre_ext.startswith("."):
                repre_ext = repre_ext[1:]

            if repre_ext != "psd":
                continue

            # Prepare json filepath where extracted metadata are stored
            json_filename = "{}.json".format(instance.name)
            json_full_path = os.path.join(staging_dir, json_filename)

            self.log.debug(f"`staging_dir` is \"{staging_dir}\"")

            # Prepare new repre data
            new_repre = {
                "name": "json",
                "ext": "json",
                "files": json_filename,
                "stagingDir": staging_dir
            }

            # TODO add check of list
            psd_filename = repre["files"]
            psd_folder_path = repre["stagingDir"]
            psd_filepath = os.path.join(psd_folder_path, psd_filename)
            self.log.debug(f"psd_filepath: \"{psd_filepath}\"")
            psd_object = PSDImage.open(psd_filepath)

            json_data, transfers = self.export_compositing_images(
                psd_object, staging_dir, publish_dir
            )
            self.log.info("Json file path: {}".format(json_full_path))
            with open(json_full_path, "w") as json_filestream:
                json.dump(json_data, json_filestream, indent=4)

            instance.data["transfers"].extend(transfers)
            instance.data["representations"].remove(repre)
            instance.data["representations"].append(new_repre)

    def export_compositing_images(self, psd_object, output_dir, publish_dir):
        json_data = {
            "__schema_version__": 1,
            "children": []
        }
        output_ext = ".png"

        to_export = []
        for layer_idx, layer in enumerate(psd_object):
            layer_name = layer.name.replace(" ", "_")
            if (
                not layer.is_visible()
                or layer_name.lower() not in self.allowed_group_names
            ):
                continue

            has_size = layer.width > 0 and layer.height > 0
            if not has_size:
                self.log.debug((
                    "Skipping layer \"{}\" because does not have any content."
                ).format(layer.name))
                continue

            filebase = "{:0>2}_{}".format(layer_idx, layer_name)
            if layer_name.lower() == "anim":
                if not layer.is_group:
                    self.log.warning("ANIM layer is not a group layer.")
                    continue

                children = []
                for anim_idx, anim_layer in enumerate(layer):
                    anim_layer_name = anim_layer.name.replace(" ", "_")
                    filename = "{}_{:0>2}_{}{}".format(
                        filebase, anim_idx, anim_layer_name, output_ext
                    )
                    children.append({
                        "index": anim_idx,
                        "name": anim_layer.name,
                        "filename": filename
                    })
                    to_export.append((anim_layer, filename))

                json_data["children"].append({
                    "index": layer_idx,
                    "name": layer.name,
                    "children": children
                })
                continue

            filename = filebase + output_ext
            json_data["children"].append({
                "index": layer_idx,
                "name": layer.name,
                "filename": filename
            })
            to_export.append((layer, filename))

        transfers = []
        for layer, filename in to_export:
            output_filepath = os.path.join(output_dir, filename)
            dst_filepath = os.path.join(publish_dir, filename)
            transfers.append((output_filepath, dst_filepath))

            pil_object = layer.composite(viewport=psd_object.viewbox)
            pil_object.save(output_filepath, "PNG")

        return json_data, transfers

    def redo_global_plugins(self, instance):
        # TODO do this in collection phase
        # Copy `families` and check if `family` is not in current families
        families = instance.data.get("families") or list()
        if families:
            families = list(set(families))

        if self.new_instance_family in families:
            families.remove(self.new_instance_family)

        self.log.debug(
            "Setting new instance families {}".format(str(families))
        )
        instance.data["families"] = families

        # Override instance data with new information
        instance.data["family"] = self.new_instance_family

        subset_name = instance.data["anatomyData"]["subset"]
        asset_doc = instance.data["assetEntity"]
        latest_version = self.find_last_version(subset_name, asset_doc)
        version_number = 1
        if latest_version is not None:
            version_number += latest_version

        instance.data["latestVersion"] = latest_version
        instance.data["version"] = version_number

        # Same data apply to anatomy data
        instance.data["anatomyData"].update({
            "family": self.new_instance_family,
            "version": version_number
        })

        # Redo publish and resources dir
        anatomy = instance.context.data["anatomy"]
        template_data = copy.deepcopy(instance.data["anatomyData"])
        template_data.update({
            "frame": "FRAME_TEMP",
            "representation": "TEMP"
        })
        anatomy_filled = anatomy.format(template_data)
        if "folder" in anatomy.templates["publish"]:
            publish_folder = anatomy_filled["publish"]["folder"]
        else:
            publish_folder = os.path.dirname(anatomy_filled["publish"]["path"])

        publish_folder = os.path.normpath(publish_folder)
        resources_folder = os.path.join(publish_folder, "resources")

        instance.data["publishDir"] = publish_folder
        instance.data["resourcesDir"] = resources_folder

        self.log.debug("publishDir: \"{}\"".format(publish_folder))
        self.log.debug("resourcesDir: \"{}\"".format(resources_folder))

    def find_last_version(self, subset_name, asset_doc):
        subset_doc = legacy_io.find_one({
            "type": "subset",
            "name": subset_name,
            "parent": asset_doc["_id"]
        })

        if subset_doc is None:
            self.log.debug("Subset entity does not exist yet.")
        else:
            version_doc = legacy_io.find_one(
                {
                    "type": "version",
                    "parent": subset_doc["_id"]
                },
                sort=[("name", -1)]
            )
            if version_doc:
                return int(version_doc["name"])
        return None
