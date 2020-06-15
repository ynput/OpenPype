import os

import clique

import pype.api
import pype.lib


class ExtractShot(pype.api.Extractor):
    """Extract shot "mov" and "wav" files."""

    label = "Extract Shot"
    hosts = ["standalonepublisher"]
    families = ["shot"]

    def process(self, instance):
        staging_dir = self.staging_dir(instance)
        self.log.info("Outputting shot to {}".format(staging_dir))

        editorial_path = instance.context.data["editorialPath"]
        basename = os.path.splitext(os.path.basename(editorial_path))[0]

        # Generate mov file.
        fps = pype.lib.get_asset()["data"]["fps"]
        input_path = os.path.join(
            os.path.dirname(editorial_path), basename + ".mov"
        )
        shot_mov = os.path.join(staging_dir, instance.data["name"] + ".mov")
        args = [
            "ffmpeg",
            "-ss", str(instance.data["frameStart"] / fps),
            "-i", input_path,
            "-t", str(
                (instance.data["frameEnd"] - instance.data["frameStart"] + 1) /
                fps
            ),
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            shot_mov
        ]
        self.log.info(f"Processing: {args}")
        output = pype.lib._subprocess(args)
        self.log.info(output)

        instance.data["representations"].append({
            "name": "mov",
            "ext": "mov",
            "files": os.path.basename(shot_mov),
            "stagingDir": staging_dir,
            "frameStart": instance.data["frameStart"],
            "frameEnd": instance.data["frameEnd"],
            "fps": fps,
            "thumbnail": True,
            "tags": ["review", "ftrackreview"]
        })

        # Generate jpegs.
        shot_jpegs = os.path.join(
            staging_dir, instance.data["name"] + ".%04d.jpeg"
        )
        args = ["ffmpeg", "-i", shot_mov, shot_jpegs]
        self.log.info(f"Processing: {args}")
        output = pype.lib._subprocess(args)
        self.log.info(output)

        collection = clique.Collection(
            head=instance.data["name"] + ".", tail='.jpeg', padding=4
        )
        for f in os.listdir(staging_dir):
            if collection.match(f):
                collection.add(f)

        instance.data["representations"].append({
            "name": "jpeg",
            "ext": "jpeg",
            "files": list(collection),
            "stagingDir": staging_dir
        })

        # Generate wav file.
        shot_wav = os.path.join(staging_dir, instance.data["name"] + ".wav")
        args = ["ffmpeg", "-i", shot_mov, shot_wav]
        self.log.info(f"Processing: {args}")
        output = pype.lib._subprocess(args)
        self.log.info(output)

        instance.data["representations"].append({
            "name": "wav",
            "ext": "wav",
            "files": os.path.basename(shot_wav),
            "stagingDir": staging_dir
        })

        # Required for extract_review plugin (L222 onwards).
        instance.data["fps"] = fps
