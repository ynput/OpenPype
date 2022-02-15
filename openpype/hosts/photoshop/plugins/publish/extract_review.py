import os

import openpype.api
import openpype.lib
from openpype.hosts.photoshop import api as photoshop


class ExtractReview(openpype.api.Extractor):
    """
        Produce a flattened image file from all 'image' instances.

        If no 'image' instance is created, it produces flattened image from
        all visible layers.
    """

    label = "Extract Review"
    hosts = ["photoshop"]
    families = ["review"]

    # Extract Options
    jpg_options = None
    mov_options = None

    def process(self, instance):
        staging_dir = self.staging_dir(instance)
        self.log.info("Outputting image to {}".format(staging_dir))

        stub = photoshop.stub()

        layers = []
        for image_instance in instance.context:
            if image_instance.data["family"] != "image":
                continue
            layers.append(image_instance.data.get("layer"))

        # Perform extraction
        output_image = "{}.jpg".format(
            os.path.splitext(stub.get_active_document_name())[0]
        )
        output_image_path = os.path.join(staging_dir, output_image)
        with photoshop.maintained_visibility():
            if layers:
                # Hide all other layers.
                extract_ids = set([ll.id for ll in stub.
                                   get_layers_in_layers(layers)])
                self.log.debug("extract_ids {}".format(extract_ids))
                for layer in stub.get_layers():
                    # limit unnecessary calls to client
                    if layer.visible and layer.id not in extract_ids:
                        stub.set_visible(layer.id, False)

            stub.saveAs(output_image_path, 'jpg', True)

        ffmpeg_path = openpype.lib.get_ffmpeg_tool_path("ffmpeg")

        instance.data["representations"].append({
            "name": "jpg",
            "ext": "jpg",
            "files": output_image,
            "stagingDir": staging_dir,
            "tags": self.jpg_options['tags']
        })
        instance.data["stagingDir"] = staging_dir

        # Generate thumbnail.
        thumbnail_path = os.path.join(staging_dir, "thumbnail.jpg")
        args = [
            ffmpeg_path,
            "-y",
            "-i", output_image_path,
            "-vf", "scale=300:-1",
            "-vframes", "1",
            thumbnail_path
        ]
        output = openpype.lib.run_subprocess(args)

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
            ffmpeg_path,
            "-y",
            "-i", output_image_path,
            "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
            "-vframes", "1",
            mov_path
        ]
        output = openpype.lib.run_subprocess(args)
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
            "tags": self.mov_options['tags']
        })

        # Required for extract_review plugin (L222 onwards).
        instance.data["frameStart"] = 1
        instance.data["frameEnd"] = 1
        instance.data["fps"] = 25

        self.log.info(f"Extracted {instance} to {staging_dir}")
