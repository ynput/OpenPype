import os

import pype.api
import pype.lib
from avalon import photoshop


class ExtractReview(pype.api.Extractor):
    """Produce a flattened image file from all instances."""

    label = "Extract Review"
    hosts = ["photoshop"]
    families = ["review"]

    def process(self, instance):

        staging_dir = self.staging_dir(instance)
        self.log.info("Outputting image to {}".format(staging_dir))

        layers = []
        for image_instance in instance.context:
            if image_instance.data["family"] != "image":
                continue
            layers.append(image_instance[0])

        # Perform extraction
        output_image = "{} copy.jpg".format(
            os.path.splitext(photoshop.app().ActiveDocument.Name)[0]
        )
        with photoshop.maintained_visibility():
            # Hide all other layers.
            extract_ids = [
                x.id for x in photoshop.get_layers_in_layers(layers)
            ]
            for layer in photoshop.get_layers_in_document():
                if layer.id in extract_ids:
                    layer.Visible = True
                else:
                    layer.Visible = False

            photoshop.app().ActiveDocument.SaveAs(
                staging_dir, photoshop.com_objects.JPEGSaveOptions(), True
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
            "-i", os.path.join(staging_dir, output_image),
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
            "-i", os.path.join(staging_dir, output_image),
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
            "fps": 25,
            "preview": True,
            "tags": ["review", "ftrackreview"]
        })

        # Required for extract_review plugin (L222 onwards).
        instance.data["frameStart"] = 1
        instance.data["frameEnd"] = 1
        instance.data["fps"] = 25

        self.log.info(f"Extracted {instance} to {staging_dir}")
