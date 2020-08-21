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
    formats = ["png", "jpg"]

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

                save_options = {}
                if "png" in self.formats:
                    save_options["png"] = photoshop.com_objects.PNGSaveOptions()
                if "jpg" in self.formats:
                    save_options["jpg"] = photoshop.com_objects.JPEGSaveOptions()

                file_basename = os.path.splitext(
                    photoshop.app().ActiveDocument.Name
                )[0]
                for extension, save_option in save_options.items():
                    _filename = "{}.{}".format(file_basename, extension)
                    files[extension] = _filename

                    full_filename = os.path.join(staging_dir, _filename)
                    photoshop.app().ActiveDocument.SaveAs(
                        full_filename, save_option, True
                    )

        representations = []
        for extension, filename in files.items():
            representations.append({
                "name": extension,
                "ext": extension,
                "files": filename,
                "stagingDir": staging_dir
            })

        workfile_context_instance = instance.context.data.get("workfile_instance")
        if workfile_context_instance:
            if workfile_context_instance.data.get("representations"):
                workfile_context_instance.data["representations"].extend(
                    representations)
            else:
                workfile_context_instance.data["representations"] = \
                    representations
            # Required for extract_review plugin (L222 onwards).
            workfile_context_instance.data["frameStart"] = 1
            workfile_context_instance.data["frameEnd"] = 1
            workfile_context_instance.data["fps"] = 24

            # set render instance family to temp so it will not be integrated
            # and add paired_review_media to the families so IntegrateNew is not
            # performed on the scene instance
            instance.data["family"] = "temp"
            workfile_context_instance.data["families"].append("paired_review_media")
            self.log.info(f"Extracted {instance} to {staging_dir}")
        else:
            if instance.data.get("representations"):
                instance.data["representations"].extend(representations)
            else:
                instance.data["representations"] = representations

            instance.data["stagingDir"] = staging_dir

            self.log.info(f"Extracted {instance} to {staging_dir}")
