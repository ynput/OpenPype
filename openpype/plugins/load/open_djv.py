import os
from openpype.api import ApplicationManager
from openpype.pipeline import load


def existing_djv_path():
    app_manager = ApplicationManager()
    djv_list = []

    for app_name, app in app_manager.applications.items():
        if 'djv' in app_name and app.find_executable():
            djv_list.append(app_name)

    return djv_list


class OpenInDJV(load.LoaderPlugin):
    """Open Image Sequence with system default"""

    djv_list = existing_djv_path()
    families = ["*"] if djv_list else []
    representations = [
        "cin", "dpx", "avi", "dv", "gif", "flv", "mkv", "mov", "mpg", "mpeg",
        "mp4", "m4v", "mxf", "iff", "z", "ifl", "jpeg", "jpg", "jfif", "lut",
        "1dl", "exr", "pic", "png", "ppm", "pnm", "pgm", "pbm", "rla", "rpf",
        "sgi", "rgba", "rgb", "bw", "tga", "tiff", "tif", "img", "h264",
    ]

    label = "Open in DJV"
    order = -10
    icon = "play-circle"
    color = "orange"

    def load(self, context, name, namespace, data):
        directory = os.path.dirname(self.fname)
        import clique

        pattern = clique.PATTERNS["frames"]
        files = os.listdir(directory)
        collections, remainder = clique.assemble(
            files,
            patterns=[pattern],
            minimum_items=1
        )

        if not remainder:
            sequence = collections[0]
            first_image = list(sequence)[0]
        else:
            first_image = self.fname
        filepath = os.path.normpath(os.path.join(directory, first_image))

        self.log.info("Opening : {}".format(filepath))

        last_djv_version = sorted(self.djv_list)[-1]

        app_manager = ApplicationManager()
        djv = app_manager.applications.get(last_djv_version)
        djv.arguments.append(filepath)

        app_manager.launch(last_djv_version)
