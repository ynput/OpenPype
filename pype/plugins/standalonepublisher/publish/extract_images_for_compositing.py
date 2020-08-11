import os
import json
import pype.api

PSDImage = None


class ExtractImagesForComp(pype.api.Extractor):
    label = "Extract Images for Compositing"
    families = ["imageForComp"]
    hosts = ["standalonepublisher"]

    # Presetable
    allowed_group_names = ["OL", "BG", "MG", "FG", "UL", "SKY", "Field Guide"]

    def process(self, instance):
        instance.context.remove(instance)
        self.log.info("NOT IMPLEMENTED YET")
        return

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

            # Prepare staging dir
            staging_dir = self.staging_dir(instance)
            if not os.path.exists(staging_dir):
                os.makedirs(staging_dir)

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

            with open(json_full_path, "w") as json_filestream:
                json.dump(json_data, json_filestream, indent=4)

            instance.data["transfers"] = transfers
            instance.data["representations"].append(new_repre)
            instance.data["representations"].remove(repre)

    def export_compositing_images(self, psd_object, output_dir, publish_dir):
        json_data = {
            "__version__": 1,
            "children_layers": []
        }
        transfers = []
        for main_idx, main_layer in enumerate(psd_object):
            if (
                not main_layer.is_visible()
                or main_layer.name not in self.allowed_group_names
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
                "children_layers": []
            }

            for layer_idx, layer in export_layers:
                filename = "{:0>2}_{}_{:0>2}_{}.png".format(
                    main_idx + 1, main_layer.name, layer_idx + 1, layer.name
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

                main_layer_data["children_layers"].append(layer_data)

            json_data["children_layers"].append(main_layer_data)

        return json_data, transfers
