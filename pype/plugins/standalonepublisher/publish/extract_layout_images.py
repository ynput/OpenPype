import os
import copy
import pype.api
import pyblish.api
from avalon import io

PSDImage = None


class ExtractImageForLayout(pype.api.Extractor):

    label = "Extract Images for Layout"
    order = pyblish.api.ExtractorOrder + 0.02
    families = ["imageForLayout"]
    hosts = ["standalonepublisher"]

    new_instance_family = "image"
    ignored_instance_data_keys = ("name", "label", "stagingDir", "version")

    # Presetable
    allowed_group_names = ["OL", "BG", "MG", "FG", "UL", "SKY", "Field Guide"]

    def process(self, instance):
        # Check if python module `psd_tools` is installed
        try:
            global PSDImage
            from psd_tools import PSDImage
        except Exception:
            raise AssertionError(
                "BUG: Python module `psd-tools` is not installed!"
            )

        repres = instance.data.get("representations")
        if not repres:
            self.log.info("There are no representations on instance.")
            return

        for repre in tuple(repres):
            # Skip all non files without .psd extension
            if repre["ext"] != ".psd":
                continue

            # TODO add check of list
            psd_filename = repre["files"]
            psd_folder_path = repre["stagingDir"]
            psd_filepath = os.path.join(psd_folder_path, psd_filename)
            self.log.debug(f"psd_filepath: \"{psd_filepath}\"")
            psd_object = PSDImage.open(psd_filepath)

            self.create_new_instances(instance, psd_object)

        # Remove the instance from context
        instance.context.remove(instance)

    def create_new_instances(self, instance, psd_object):
        asset_doc = instance.data["assetEntity"]
        for layer in psd_object:
            if (
                not layer.is_visible()
                or layer.name not in self.allowed_group_names
            ):
                continue

            layer_name = layer.name.replace(" ", "_")
            instance_name = subset_name = f"image{layer_name}"
            self.log.info(
                f"Creating new instance with name \"{instance_name}\""
            )
            new_instance = instance.context.create_instance(instance_name)
            for key, value in instance.data.items():
                if key not in self.ignored_instance_data_keys:
                    new_instance.data[key] = copy.deepcopy(value)

            new_instance.data["label"] = " ".join(
                (new_instance.data["asset"], instance_name)
            )

            # Find latest version
            version_number = self.find_latest_version(subset_name, asset_doc)
            self.log.info(
                "Next version of instance \"{}\" will be {}".format(
                    instance_name, version_number
                )
            )

            # Set family and subset
            new_instance.data["family"] = self.new_instance_family
            new_instance.data["subset"] = subset_name
            new_instance.data["version"] = version_number

            new_instance.data["anatomyData"].update({
                "subset": subset_name,
                "family": self.new_instance_family,
                "version": version_number
            })

            # Copy `families` and check if `family` is not in current families
            families = new_instance.data.get("families") or list()
            if families:
                families = list(set(families))

            if self.new_instance_family in families:
                families.remove(self.new_instance_family)
            new_instance.data["families"] = families

            # Prepare staging dir for new instance
            staging_dir = self.staging_dir(new_instance)

            output_filename = "{}.png".format(layer_name)
            output_filepath = os.path.join(staging_dir, output_filename)
            pil_object = layer.composite(viewport=psd_object.viewbox)
            pil_object.save(output_filepath, "PNG")

            new_repre = {
                "name": "png",
                "ext": "png",
                "files": output_filename,
                "stagingDir": staging_dir
            }
            new_instance.data["representations"] = [new_repre]
            self.log.debug(new_instance.data["name"])

    def find_latest_version(self, subset_name, asset_doc):
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
                return int(version_doc["name"]) + 1
        return 1
