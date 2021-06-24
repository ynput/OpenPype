"""
transcode.py -input "input.%04d.exr [1-77]" -name name
-preset prores422HQ review -output path/to/output/folder

transcode.py -input input.mov -name name
-preset prores422HQ review -output path/to/output/folder

transcode.py -input input.txt -name name
-preset concat -output path/to/output/folder

Concatenation *.txt files follows syntax from the FFMPEG demuxer guide;
https://trac.ffmpeg.org/wiki/Concatenate
"""
import os
import sys
import argparse
import tempfile

import clique
from pype import lib


preset_templates = {
    "prores422HQ": {
        "args": [
            "-c:v", "prores_ks",
            "-profile:v", "3",
            "-pix_fmt", "yuv422p10le",
            "-qscale:v", "5",
            "-codec:a", "pcm_s16le"
        ],
        "extension": ".mov"
    },
    "proresProxy": {
        "args": [
            "-c:v", "prores_ks",
            "-profile:v", "0",
            "-pix_fmt", "yuv422p10le",
            "-qscale:v", "5",
            "-codec:a", "pcm_s16le",
            "-vf", "scale=trunc(oh*a/2)*2:trunc(ih/2)"
        ],
        "extension": ".mov"
    },
    "h264": {
        "args": ["-crf", "18", "-pix_fmt", "yuv420p"],
        "extension": ".mov"
    },
    "concat": {
        "args": ["-c", "copy"],
        "extension": ".mov"
    }
}


def main(input_path="",
         preset="",
         name="",
         output_path="",
         audio_path="",
         start=None,
         end=None,
         framerate=None):

    collection = None
    try:
        collection = clique.parse(input_path)
    except ValueError:
        pass

    first_file = input_path
    if collection:
        first_file = list(collection)[0]

    output_path = os.path.join(
        output_path, name + preset_templates[preset]["extension"]
    ).replace("//", "/")

    # Ensure output directory exists.
    if not os.path.exists(os.path.dirname(output_path)):
        os.makedirs(os.path.dirname(output_path))

    # Build ffmpeg arguments.
    ffmpeg_args = ["ffmpeg", "-y"]

    # Add audio.
    if audio_path:
        ffmpeg_args.extend(["-ss", str(abs(int(start) / float(framerate)))])
        ffmpeg_args.extend(["-i", audio_path])

    temp_files = []

    # Process EXRs.
    if first_file.endswith(".exr"):
        # Ensure for ffmpeg compatibility.
        output = lib._subprocess(["oiiotool", "--info", "-v", first_file])
        if "compression: \"dwaa\"" in output:
            dirpath = tempfile.mkdtemp()
            head = os.path.join(dirpath, name + ".").replace("//", "/")
            args = [
                "oiiotool",
                "--frames",
                "{}-{}".format(
                    list(collection.indexes)[0], list(collection.indexes)[-1]
                ),
                collection.format("{head}{padding}{tail}"),
                "--compression", "none",
                "-o", collection.format(head + "{padding}{tail}")
            ]
            print("Running: {}".format(" ".join(args)))
            lib._subprocess(args)

            collection = clique.parse(
                "{} [{}-{}]".format(
                    collection.format(head + "{padding}{tail}"),
                    list(collection.indexes)[0],
                    list(collection.indexes)[-1]
                )
            )

            for item in collection:
                temp_files.append(item)

        # Add EXR ffmpeg args.
        ffmpeg_args.extend(
            [
                "-gamma", "2.2",
                "-start_number", str(list(collection.indexes)[0]),
                "-i", collection.format("{head}{padding}{tail}")
            ]
        )

    # Process movie files.
    supported_extensions = [".mov", ".mp4"]
    if os.path.splitext(first_file)[1] in supported_extensions:

        # TODO: Copying file if its compatible with the destination codec.

        if start:
            ffmpeg_args.extend(
                ["-ss", str(abs(int(start) / float(framerate)))]
            )

        if end:
            ffmpeg_args.extend(
                ["-to", str(abs(int(end) / float(framerate)))]
            )

        ffmpeg_args.extend(["-i", first_file])

    # Process TXTs.
    if first_file.endswith(".txt"):
        ffmpeg_args.extend(
            ["-f", "concat", "-safe", "0", "-i", os.path.basename(first_file)]
        )

    # Process preset.
    args = list(ffmpeg_args)

    if not audio_path:
        args += ["-an"]

    args += preset_templates[preset]["args"]
    args += ["-shortest", output_path]
    print("Running: {}".format(" ".join(args)))
    lib._subprocess(args, cwd=os.path.dirname(first_file))

    # Clean up temporary files.
    for item in temp_files:
        os.remove(item)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Transcoder")

    parser.add_argument("-input", action="store", dest="input_path")
    parser.add_argument("-preset", action="store", dest="preset")
    parser.add_argument("-name", action="store", dest="name")
    parser.add_argument("-audio", nargs="?", dest="audio_path")
    parser.add_argument("-start", action="store", dest="start")
    parser.add_argument("-end", action="store", dest="end")
    parser.add_argument("-framerate", action="store", dest="framerate")
    parser.add_argument("-output", action="store", dest="output_path")

    kwargs = vars(parser.parse_args(sys.argv[1:]))

    main(**kwargs)
