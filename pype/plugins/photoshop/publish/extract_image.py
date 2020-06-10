import os

import pype.api
from avalon import photoshop


class ExtractImage(pype.api.Extractor):
    """Produce a flattened image file from instance

    This plug-in takes into account only the layers in the group.
    """

    label = "Extract Image"
    hosts = ["photoshop"]
    families = ["image"]

    def process(self, instance):

        staging_dir = self.staging_dir(instance)
        self.log.info("Outputting image to {}".format(staging_dir))

        # Perform extraction
        files = {}
        with photoshop.maintained_selection():
            self.log.info("Extracting %s" % str(list(instance)))
            with photoshop.maintained_visibility():
                # Hide all other layers.
                extract_ids = [
                    x.id for x in photoshop.get_layers_in_layers([instance[0]])
                ]
                for layer in photoshop.get_layers_in_document():
                    if layer.id not in extract_ids:
                        layer.Visible = False

                save_options = {
                    "png": photoshop.com_objects.PNGSaveOptions(),
                    "jpg": photoshop.com_objects.JPEGSaveOptions()
                }

                for extension, save_option in save_options.items():
                    photoshop.app().ActiveDocument.SaveAs(
                        staging_dir, save_option, True
                    )
                    files[extension] = "{} copy.{}".format(
                        os.path.splitext(
                            photoshop.app().ActiveDocument.Name
                        )[0],
                        extension
                    )

        representations = []
        for extension, filename in files.items():
            representations.append({
                "name": extension,
                "ext": extension,
                "files": filename,
                "stagingDir": staging_dir
            })
        instance.data["representations"] = representations
        instance.data["stagingDir"] = staging_dir

        self.log.info(f"Extracted {instance} to {staging_dir}")
