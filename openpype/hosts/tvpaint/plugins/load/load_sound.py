import os
import tempfile
from openpype.hosts.tvpaint.api import lib, plugin


class ImportSound(plugin.Loader):
    """Load sound to TVPaint.

    Sound layers does not have ids but only position index so we can't
    reference them as we can't say which is which input.

    We might do that (in future) by input path. Which may be identifier if
    we'll allow only one loaded instance of the representation as an audio.

    This plugin does not work for all version of TVPaint. Known working
    version is TVPaint 11.0.10 .

    It is allowed to load video files as sound but it does not check if video
    file contain any audio.
    """

    families = ["audio", "review", "plate"]
    representations = ["*"]

    label = "Import Sound"
    order = 1
    icon = "image"
    color = "white"

    import_script_lines = (
        "sound_path = '\"'\"{}\"'\"'",
        "output_path = \"{}\"",
        # Try to get sound clip info to check if we are in TVPaint that can
        # load sound
        "tv_clipcurrentid",
        "clip_id = result",
        "tv_soundclipinfo clip_id 0",
        "IF CMP(result,\"\")==1",
        (
            "tv_writetextfile \"strict\" \"append\" '\"'output_path'\"'"
            " 'success|'"
        ),
        "EXIT",
        "END",

        "tv_soundclipnew sound_path",
        "line = 'success|'result",
        "tv_writetextfile \"strict\" \"append\" '\"'output_path'\"' line"
    )

    def load(self, context, name, namespace, options):
        # Create temp file for output
        output_file = tempfile.NamedTemporaryFile(
            mode="w", prefix="pype_tvp_", suffix=".txt", delete=False
        )
        output_file.close()
        output_filepath = output_file.name.replace("\\", "/")

        # Prepare george script
        import_script = "\n".join(self.import_script_lines)
        george_script = import_script.format(
            self.fname.replace("\\", "/"),
            output_filepath
        )
        self.log.info("*** George script:\n{}\n***".format(george_script))
        # Execute geoge script
        lib.execute_george_through_file(george_script)

        # Read output file
        lines = []
        with open(output_filepath, "r") as file_stream:
            for line in file_stream:
                line = line.rstrip()
                if line:
                    lines.append(line)

        # Clean up temp file
        os.remove(output_filepath)

        output = {}
        for line in lines:
            key, value = line.split("|")
            output[key] = value

        success = output.get("success")
        # Successfully loaded sound
        if success == "0":
            return

        if success == "":
            raise ValueError(
                "Your TVPaint version does not support loading of"
                " sound through George script. Please use manual load."
            )

        if success is None:
            raise ValueError(
                "Unknown error happened during load."
                " Please report and try to use manual load."
            )

        # Possible errors by TVPaint documentation
        # https://www.tvpaint.com/doc/tvpaint-animation-11/george-commands#tv_soundclipnew
        if success == "-1":
            raise ValueError(
                "BUG: George command did not get enough arguments."
            )

        if success == "-2":
            # Who know what does that mean?
            raise ValueError("No current clip without mixer.")

        if success == "-3":
            raise ValueError("TVPaint couldn't read the file.")

        if success == "-4":
            raise ValueError("TVPaint couldn't add the track.")

        raise ValueError("BUG: Unknown success value {}.".format(success))
