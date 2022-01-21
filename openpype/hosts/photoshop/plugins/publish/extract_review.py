import os
import shutil

import openpype.api
import openpype.lib
from openpype.hosts.photoshop import api as photoshop


class ExtractReview(openpype.api.Extractor):
    """
        Produce a flattened or sequence image file from all 'image' instances.

        If no 'image' instance is created, it produces flattened image from
        all visible layers.
    """

    label = "Extract Review"
    hosts = ["photoshop"]
    families = ["review"]

    # Extract Options
    jpg_options = None
    mov_options = None
    make_image_sequence = None

    def process(self, instance):
        staging_dir = self.staging_dir(instance)
        self.log.info("Outputting image to {}".format(staging_dir))

        stub = photoshop.stub()
        self.output_seq_filename = os.path.splitext(
            stub.get_active_document_name())[0] + ".%04d.jpg"

        new_img_list = src_img_list = []
        if self.make_image_sequence:
            src_img_list = self._get_image_path_from_instances(instance)
        if self.make_image_sequence and src_img_list:
            new_img_list = self._copy_image_to_staging_dir(
                staging_dir,
                src_img_list
            )
        else:
            layers = self._get_layers_from_instance(instance)
            new_img_list = self._saves_flattened_layers(staging_dir, layers)
            instance.data["representations"].append({
                "name": "jpg",
                "ext": "jpg",
                "files": new_img_list,
                "stagingDir": staging_dir,
                "tags": self.jpg_options['tags']
            })

        ffmpeg_path = openpype.lib.get_ffmpeg_tool_path("ffmpeg")

        instance.data["stagingDir"] = staging_dir

        # Generate thumbnail.
        thumbnail_path = os.path.join(staging_dir, "thumbnail.jpg")
        self.log.info(f"Generate thumbnail {thumbnail_path}")
        args = [
            ffmpeg_path,
            "-y",
            "-i", os.path.join(staging_dir, self.output_seq_filename),
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
        self.log.info(f"Generate mov review: {mov_path}")
        img_number = len(new_img_list)
        args = [
            ffmpeg_path,
            "-y",
            "-i", os.path.join(staging_dir, self.output_seq_filename),
            "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
            "-vframes", str(img_number),
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
            "frameEnd": img_number,
            "fps": 25,
            "preview": True,
            "tags": self.mov_options['tags']
        })

        # Required for extract_review plugin (L222 onwards).
        instance.data["frameStart"] = 1
        instance.data["frameEnd"] = img_number
        instance.data["fps"] = 25

        self.log.info(f"Extracted {instance} to {staging_dir}")

    def _get_image_path_from_instances(self, instance):
        img_list = []

        for instance in instance.context:
            if instance.data["family"] != "image":
                continue

            for rep in instance.data["representations"]:
                img_path = os.path.join(
                    rep["stagingDir"],
                    rep["files"]
                )
                img_list.append(img_path)

        return img_list

    def _copy_image_to_staging_dir(self, staging_dir, img_list):
        copy_files = []
        for i, img_src in enumerate(img_list):
            img_filename = self.output_seq_filename % i
            img_dst = os.path.join(staging_dir, img_filename)

            self.log.debug(
                "Copying file .. {} -> {}".format(img_src, img_dst)
            )
            shutil.copy(img_src, img_dst)
            copy_files.append(img_filename)

        return copy_files

    def _get_layers_from_instance(self, instance):
        layers = []
        for image_instance in instance.context:
            if image_instance.data["family"] != "image":
                continue
            layers.append(image_instance[0])

        return layers

    def _saves_flattened_layers(self, staging_dir, layers):
        img_filename = self.output_seq_filename % 0
        output_image_path = os.path.join(staging_dir, img_filename)
        stub = photoshop.stub()

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

        return img_filename
