import os
import json
import copy
import pype.api
from avalon import io

PSDImage = None


class ExtractBGForComp(pype.api.Extractor):
    label = "Extract Background for Compositing"
    families = ["backgroundComp"]
    hosts = ["standalonepublisher"]

    new_instance_family = "background"

    # Presetable
    allowed_group_names = [
        "OL", "BG", "MG", "FG", "SB", "UL", "SKY", "Field Guide", "Field_Guide",
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

        for repre in tuple(repres):
            # Skip all files without .psd extension
            if repre["ext"] != ".psd":
                continue

            # Prepare publish dir for transfers
            publish_dir = instance.data["publishDir"]

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
        transfers = []
        for main_idx, main_layer in enumerate(psd_object):
            if (
                not main_layer.is_visible()
                or main_layer.name.lower() not in self.allowed_group_names
                or not main_layer.is_group
            ):
                continue

            export_layers = []
            layers_idx = 0
            for layer in main_layer:
                # TODO this way may be added also layers next to "ADJ"
                if layer.name.lower() == "adj":
                    for _layer in layer:
                        export_layers.append((layers_idx, _layer))
                        layers_idx += 1

                else:
                    export_layers.append((layers_idx, layer))
                    layers_idx += 1

            if not export_layers:
                continue

            main_layer_data = {
                "index": main_idx,
                "name": main_layer.name,
                "children": []
            }

            for layer_idx, layer in export_layers:
                has_size = layer.width > 0 and layer.height > 0
                if not has_size:
                    self.log.debug((
                        "Skipping layer \"{}\" because does "
                        "not have any content."
                    ).format(layer.name))
                    continue

                main_layer_name = main_layer.name.replace(" ", "_")
                layer_name = layer.name.replace(" ", "_")

                filename = "{:0>2}_{}_{:0>2}_{}.png".format(
                    main_idx + 1, main_layer_name, layer_idx + 1, layer_name
                )
                layer_data = {
                    "index": layer_idx,
                    "name": layer.name,
                    "filename": filename
                }
                output_filepath = os.path.join(output_dir, filename)
                dst_filepath = os.path.join(publish_dir, filename)
                transfers.append((output_filepath, dst_filepath))

                pil_object = layer.composite(viewport=psd_object.viewbox)
                pil_object.save(output_filepath, "PNG")

                main_layer_data["children"].append(layer_data)

            if main_layer_data["children"]:
                json_data["children"].append(main_layer_data)

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
        subset_doc = io.find_one({
            "type": "subset",
            "name": subset_name,
            "parent": asset_doc["_id"]
        })

        if subset_doc is None:
            self.log.debug("Subset entity does not exist yet.")
        else:
            version_doc = io.find_one(
                {
                    "type": "version",
                    "parent": subset_doc["_id"]
                },
                sort=[("name", -1)]
            )
            if version_doc:
                return int(version_doc["name"])
        return None
