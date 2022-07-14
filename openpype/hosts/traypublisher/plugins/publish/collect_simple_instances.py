import os

import clique
import pyblish.api


class CollectSettingsSimpleInstances(pyblish.api.InstancePlugin):
    """Collect data for instances created by settings creators."""

    label = "Collect Settings Simple Instances"
    order = pyblish.api.CollectorOrder - 0.49

    hosts = ["traypublisher"]

    _image_extensions = [
        ".ani", ".anim", ".apng", ".art", ".bmp", ".bpg", ".bsave", ".cal",
        ".cin", ".cpc", ".cpt", ".dds", ".dpx", ".ecw", ".exr", ".fits",
        ".flic", ".flif", ".fpx", ".gif", ".hdri", ".hevc", ".icer",
        ".icns", ".ico", ".cur", ".ics", ".ilbm", ".jbig", ".jbig2",
        ".jng", ".jpeg", ".jpeg-ls", ".jpeg", ".2000", ".jpg", ".xr",
        ".jpeg", ".xt", ".jpeg-hdr", ".kra", ".mng", ".miff", ".nrrd",
        ".ora", ".pam", ".pbm", ".pgm", ".ppm", ".pnm", ".pcx", ".pgf",
        ".pictor", ".png", ".psb", ".psp", ".qtvr", ".ras",
        ".rgbe", ".logluv", ".tiff", ".sgi", ".tga", ".tiff", ".tiff/ep",
        ".tiff/it", ".ufo", ".ufp", ".wbmp", ".webp", ".xbm", ".xcf",
        ".xpm", ".xwd"
    ]
    _video_extensions = [
        ".3g2", ".3gp", ".amv", ".asf", ".avi", ".drc", ".f4a", ".f4b",
        ".f4p", ".f4v", ".flv", ".gif", ".gifv", ".m2v", ".m4p", ".m4v",
        ".mkv", ".mng", ".mov", ".mp2", ".mp4", ".mpe", ".mpeg", ".mpg",
        ".mpv", ".mxf", ".nsv", ".ogg", ".ogv", ".qt", ".rm", ".rmvb",
        ".roq", ".svi", ".vob", ".webm", ".wmv", ".yuv"
    ]
    _review_extensions = _image_extensions + _video_extensions

    def process(self, instance):
        if not instance.data.get("settings_creator"):
            return

        # Create instance's staging dir in temp
        tmp_folder = tempfile.mkdtemp(prefix="traypublisher_")
        instance.data["stagingDir"] = tmp_folder
        instance.context.data["cleanupFullPaths"].append(tmp_folder)

        self.log.debug(
            "Created temp staging directory for instance {}".format(tmp_folder)
        )

        repres = instance.data["representations"]

        creator_attributes = instance.data["creator_attributes"]
        filepath_item = creator_attributes["filepath"]
        self.log.info(filepath_item)
        filepaths = [
            os.path.join(filepath_item["directory"], filename)
            for filename in filepath_item["filenames"]
        ]

        cols, rems = clique.assemble(filepaths)
        source = None
        if cols:
            source = cols[0].format("{head}{padding}{tail}")
        elif rems:
            source = rems[0]

        instance.data["source"] = source
        instance.data["sourceFilepaths"] = filepaths

        filenames = filepath_item["filenames"]
        _, ext = os.path.splitext(filenames[0])
        ext = ext[1:]
        if len(filenames) == 1:
            filenames = filenames[0]

        repres.append({
            "ext": ext,
            "name": ext,
            "stagingDir": filepath_item["directory"],
            "files": filenames
        })

        instance.data["source"] = "\n".join(filepaths)

        self.log.debug("Created Simple Settings instance {}".format(
            instance.data
        ))
