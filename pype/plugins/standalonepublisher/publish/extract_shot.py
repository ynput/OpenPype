import os
import clique
import pype.api
import pype.lib as plib


class ExtractShot(pype.api.Extractor):
    """Extract shot "mov" and "wav" files."""

    label = "Extract Shot"
    hosts = ["standalonepublisher"]
    families = ["clip"]

    def process(self, instance):
        # get ffmpet path
        ffmpeg_path = pype.lib.get_ffmpeg_tool_path("ffmpeg")

        # get staging dir
        staging_dir = self.staging_dir(instance)
        self.log.info("Staging dir set to: `{}`".format(staging_dir))

        # Generate mov file.
        fps = instance.data["fps"]
        video_file_path = instance.data["editorialVideoPath"]
        ext = os.path.splitext(os.path.basename(video_file_path))[-1]

        clip_trimed_path = os.path.join(
            staging_dir, instance.data["name"] + ext)

        # check video file metadata
        input_data = plib.ffprobe_streams(video_file_path)[0]
        self.log.debug(f"__ input_data: `{input_data}`")

        args = [
            ffmpeg_path,
            "-ss", str(instance.data["clipIn"] / fps),
            "-i", video_file_path,
            "-t", str(
                (instance.data["clipOut"] - instance.data["clipIn"] + 1) /
                fps
            ),
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            clip_trimed_path
        ]
        self.log.info(f"Processing: {args}")
        ffmpeg_args = " ".join(args)
        output = pype.api.subprocess(ffmpeg_args)
        self.log.info(output)

        instance.data["representations"].append({
            "name": ext[1:],
            "ext": ext[1:],
            "files": os.path.basename(clip_trimed_path),
            "stagingDir": staging_dir,
            "frameStart": instance.data["frameStart"],
            "frameEnd": instance.data["frameEnd"],
            "fps": fps,
            "thumbnail": True,
            "tags": ["review", "ftrackreview", "delete"]
        })

        # # Generate jpegs.
        # clip_thumbnail = os.path.join(
        #     staging_dir, instance.data["name"] + ".%04d.jpeg"
        # )
        # args = [ffmpeg_path, "-i", clip_trimed_path, clip_thumbnail]
        # self.log.info(f"Processing: {args}")
        # output = pype.lib._subprocess(args)
        # self.log.info(output)
        #
        # # collect jpeg sequence if editorial data for publish
        # # are image sequence
        # collection = clique.Collection(
        #     head=instance.data["name"] + ".", tail='.jpeg', padding=4
        # )
        # for f in os.listdir(staging_dir):
        #     if collection.match(f):
        #         collection.add(f)
        #
        # instance.data["representations"].append({
        #     "name": "jpeg",
        #     "ext": "jpeg",
        #     "files": list(collection),
        #     "stagingDir": staging_dir
        # })
        #
        # # Generate wav file.
        # shot_wav = os.path.join(staging_dir, instance.data["name"] + ".wav")
        # args = [ffmpeg_path, "-i", clip_trimed_path, shot_wav]
        # self.log.info(f"Processing: {args}")
        # output = pype.lib._subprocess(args)
        # self.log.info(output)
        #
        # instance.data["representations"].append({
        #     "name": "wav",
        #     "ext": "wav",
        #     "files": os.path.basename(shot_wav),
        #     "stagingDir": staging_dir
        # })
