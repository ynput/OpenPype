import os
import subprocess
from avalon import api


def existing_djv_path():
    djv_paths = os.environ.get("DJV_PATH") or ""
    for path in djv_paths.split(os.pathsep):
        if os.path.exists(path):
            return path
    return None


class OpenInDJV(api.Loader):
    """Open Image Sequence with system default"""

    djv_path = existing_djv_path()
    families = ["*"] if djv_path else []
    representations = [
        "cin", "dpx", "avi", "dv", "gif", "flv", "mkv", "mov", "mpg", "mpeg",
        "mp4", "m4v", "mxf", "iff", "z", "ifl", "jpeg", "jpg", "jfif", "lut",
        "1dl", "exr", "pic", "png", "ppm", "pnm", "pgm", "pbm", "rla", "rpf",
        "sgi", "rgba", "rgb", "bw", "tga", "tiff", "tif", "img"
    ]

    label = "Open in DJV"
    order = -10
    icon = "play-circle"
    color = "orange"

    def load(self, context, name, namespace, data):
        directory = os.path.dirname(self.fname)
        from avalon.vendor import clique

        pattern = clique.PATTERNS["frames"]
        files = os.listdir(directory)
        collections, remainder = clique.assemble(
            files,
            patterns=[pattern],
            minimum_items=1
        )

        if not remainder:
            seqeunce = collections[0]
            first_image = list(seqeunce)[0]
        else:
            first_image = self.fname
        filepath = os.path.normpath(os.path.join(directory, first_image))

        self.log.info("Opening : {}".format(filepath))

        cmd = [
            # DJV path
            os.path.normpath(self.djv_path),
            # PATH TO COMPONENT
            os.path.normpath(filepath)
        ]

        # Run DJV with these commands
        subprocess.Popen(cmd)
