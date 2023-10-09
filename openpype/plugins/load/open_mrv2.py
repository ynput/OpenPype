import os
from openpype.lib import ApplicationManager


from openpype.pipeline import load


class OpenInMRV2(load.LoaderPlugin):
    """Open Image Sequence with MRV2"""
    families = ["*"]
    representations = ["*"]
    extensions = {
        "cin", "dpx", "avi", "dv", "gif", "flv", "mkv", "mov", "mpg", "mpeg",
        "mp4", "m4v", "mxf", "iff", "z", "ifl", "jpeg", "jpg", "jfif", "lut",
        "1dl", "exr", "pic", "png", "ppm", "pnm", "pgm", "pbm", "rla", "rpf",
        "sgi", "rgba", "rgb", "bw", "tga", "tiff", "tif", "img", "h264",
    }

    label = "Open in MRV2"
    order = 2
    icon = "play-circle"
    color = "orange"

    # Set via `apply_settings`
    executables = []
    app_manager = None

    @classmethod
    def apply_settings(cls, project_settings, system_settings):
        app_manager = ApplicationManager(system_settings=system_settings)

        executables = []
        for app_name, app in app_manager.applications.items():
            if 'mrv2' in app_name and app.find_executable():
                executables.append(app_name)

        cls.executables = executables
        cls.app_manager = app_manager
        if not executables:
            cls.enabled = False
            cls.families = ["*"]

    def load(self, context, name, namespace, data):
        import clique

        path = self.filepath_from_context(context)
        directory = os.path.dirname(path)

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
            first_image = path
        filepath = os.path.normpath(os.path.join(directory, first_image))

        app_args = []

        # Use representation colorspace if defined
        colorspace_data = self.get_colorspace_data(context)
        if colorspace_data:
            # TODO: The path should actually be retrieved through the template
            config_path = colorspace_data["config"]["path"]
            if os.path.exists(config_path):
                app_args.extend([
                    "-colorConfig", config_path,
                    "-colorInput", colorspace_data["colorspace"],
                    "-colorDisplay", colorspace_data["display"],
                    "-colorView", colorspace_data["view"]
                ])
            else:
                self.log.warning(
                    f"OCIO Colorspace data found for file, but OCIO config "
                    f"path not found on disk: {config_path}. "
                    f"Ignoring colorspace data."
                )

        # Match publish fps if possible
        fps = self.get_fps(context)
        app_args.extend(["-speed", str(fps)])

        # Launch with the provided file
        app_args.append(filepath)

        self.log.info("Opening : {}".format(filepath))
        last_executable_version = sorted(self.executables)[-1]

        self.app_manager.launch(last_executable_version,
                                # Additional data for launch
                                **dict(
                                    app_args=app_args,
                                    start_last_workfile=False
                                ))

    def get_colorspace_data(self, context):
        """Return colorspace of the file to load.

        Retrieves the explicit colorspace from the publish.

        Returns:
            dict or None: The colorspace data or None if not detected.

        """
        representation = context["representation"]
        colorspace_data = representation.get("data", {}).get("colorspaceData")
        if colorspace_data:
            # Example data:
            # "colorspaceData": {
            #     "colorspace": "ACEScg",
            #     "config": {
            #         "path": "/path/to/config.ocio",
            #         "template": "{template}/to/config.ocio"
            #     },
            #     "display": "sRGB",
            #     "view": "ACES 1.0 SDR-video"
            # },
            return colorspace_data

    def get_fps(self, context, default=25):

        for entity in ["representation", "version", "asset", "project"]:
            fps = context[entity].get("data", {}).get("fps")
            if fps is not None:
                self.log.info(f"Using FPS from {entity}: {fps}")
                return fps

        self.log.warning(f"Using fallback default FPS: {fps}")
        return default
