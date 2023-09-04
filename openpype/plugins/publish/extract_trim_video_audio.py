import os
from pprint import pformat

import pyblish.api

from openpype.lib import (
    get_ffmpeg_tool_args,
    run_subprocess,
)
from openpype.pipeline import publish


class ExtractTrimVideoAudio(publish.Extractor):
    """Trim with ffmpeg "mov" and "wav" files."""

    # must be before `ExtractThumbnailSP`
    order = pyblish.api.ExtractorOrder - 0.01
    label = "Extract Trim Video/Audio"
    hosts = ["standalonepublisher", "traypublisher"]
    families = ["clip", "trimming"]

    # make sure it is enabled only if at least both families are available
    match = pyblish.api.Subset

    # presets

    def process(self, instance):
        representation = instance.data.get("representations")
        self.log.debug(f"_ representation: {representation}")

        if not representation:
            instance.data["representations"] = list()

        # get ffmpet path
        ffmpeg_tool_args = get_ffmpeg_tool_args("ffmpeg")

        # get staging dir
        staging_dir = self.staging_dir(instance)
        self.log.info("Staging dir set to: `{}`".format(staging_dir))

        # Generate mov file.
        fps = instance.data["fps"]
        video_file_path = instance.data["editorialSourcePath"]
        extensions = instance.data.get("extensions", ["mov"])
        output_file_type = instance.data.get("outputFileType")
        reviewable = "review" in instance.data["families"]

        frame_start = int(instance.data["frameStart"])
        frame_end = int(instance.data["frameEnd"])
        handle_start = instance.data["handleStart"]
        handle_end = instance.data["handleEnd"]

        clip_start_h = float(instance.data["clipInH"])
        _dur = instance.data["clipDuration"]
        handle_dur = (handle_start + handle_end)
        clip_dur_h = float(_dur + handle_dur)

        if output_file_type:
            extensions = [output_file_type]

        for ext in extensions:
            self.log.info("Processing ext: `{}`".format(ext))

            if not ext.startswith("."):
                ext = "." + ext

            clip_trimed_path = os.path.join(
                staging_dir, instance.data["name"] + ext)

            if ext == ".wav":
                # offset time as ffmpeg is having bug
                clip_start_h += 0.5
                # remove "review" from families
                instance.data["families"] = [
                    fml for fml in instance.data["families"]
                    if "trimming" not in fml
                ]

            ffmpeg_args = ffmpeg_tool_args + [
                "-ss", str(clip_start_h / fps),
                "-i", video_file_path,
                "-t", str(clip_dur_h / fps)
            ]
            if ext in [".mov", ".mp4"]:
                ffmpeg_args.extend([
                    "-crf", "18",
                    "-pix_fmt", "yuv420p"
                ])
            elif ext in ".wav":
                ffmpeg_args.extend([
                    "-vn",
                    "-acodec", "pcm_s16le",
                    "-ar", "48000",
                    "-ac", "2"
                ])

            # add output path
            ffmpeg_args.append(clip_trimed_path)

            joined_args = " ".join(ffmpeg_args)
            self.log.info(f"Processing: {joined_args}")
            run_subprocess(
                ffmpeg_args, logger=self.log
            )

            repre = {
                "name": ext[1:],
                "ext": ext[1:],
                "files": os.path.basename(clip_trimed_path),
                "stagingDir": staging_dir,
                "frameStart": frame_start,
                "frameEnd": frame_end,
                "frameStartFtrack": frame_start - handle_start,
                "frameEndFtrack": frame_end + handle_end,
                "fps": fps,
                "tags": []
            }

            if ext in [".mov", ".mp4"] and reviewable:
                repre.update({
                    "thumbnail": True,
                    "tags": ["review", "ftrackreview", "delete"]})

            instance.data["representations"].append(repre)

            self.log.debug(f"Instance data: {pformat(instance.data)}")
