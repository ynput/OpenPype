import os

from avalon import photoshop

import pype.api
import pype.lib


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
        instance.data["representations"] = representations
        instance.data["stagingDir"] = staging_dir

        self.log.info(f"Extracted {instance} to {staging_dir}")

        self.create_review(instance)

    def create_review(self, instance):

        staging_dir = self.staging_dir(instance)
        self.log.info("Outputting image to {}".format(staging_dir))

        layers = []
        for image_instance in instance.context:
            if image_instance.data["family"] != "image":
                continue
            layers.append(image_instance[0])

        # Perform extraction
        output_image = "{}.jpg".format(
            os.path.splitext(photoshop.app().ActiveDocument.Name)[0]
        )
        output_image_path = os.path.join(staging_dir, output_image)
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

                for layer in photoshop.get_layers_in_document():
                    if layer.id in extract_ids:
                        layer.Visible = True
                    else:
                        layer.Visible = False

                photoshop.app().ActiveDocument.SaveAs(
                    output_image_path,
                    photoshop.com_objects.JPEGSaveOptions(),
                    True
                )

                ffmpeg_path = pype.lib.get_ffmpeg_tool_path("ffmpeg")

                instance.data["representations"].append({
                    "name": "jpg",
                    "ext": "jpg",
                    "files": output_image,
                    "stagingDir": staging_dir
                })
                instance.data["stagingDir"] = staging_dir

                # Generate thumbnail.
                thumbnail_path = os.path.join(staging_dir, "thumbnail.jpg")
                args = [
                    ffmpeg_path, "-y",
                    "-i", output_image_path,
                    "-vf", "scale=300:-1",
                    "-vframes", "1",
                    thumbnail_path
                ]
                output = pype.lib._subprocess(args)

                self.log.debug(output)

                instance.data["representations"].append({
                    "name": "thumbnail",
                    "ext": "jpg",
                    "files": os.path.basename(thumbnail_path),
                    "stagingDir": staging_dir,
                    "tags": ["thumbnail"]
                })

                # Generate mov.
                mov_path = os.path.join(staging_dir, "review.mov")
                args = [
                    ffmpeg_path, "-y",
                    "-i", output_image_path,
                    "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
                    "-vframes", "1",
                    mov_path
                ]
                output = pype.lib._subprocess(args)

                self.log.debug(output)

                instance.data["representations"].append({
                    "name": "mov",
                    "ext": "mov",
                    "files": os.path.basename(mov_path),
                    "stagingDir": staging_dir,
                    "frameStart": 1,
                    "frameEnd": 1,
                    "fps": 24,
                    "preview": True,
                    "tags": ["review", "ftrackreview"]
                })

                instance.data["frameStart"] = 1
                instance.data["frameEnd"] = 1
                instance.data["fps"] = 24
