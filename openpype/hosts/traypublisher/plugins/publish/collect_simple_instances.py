import os
import json
import tempfile

import clique
import pyblish.api


class CollectSettingsSimpleInstances(pyblish.api.InstancePlugin):
    """Collect data for instances created by settings creators.

    Plugin create representations based on 'filepath' attribute stored
    on instance.

    Representations can be marked for review and in that case is also added
    'review' family to instance families. For review can be marked only one
    representation so **first** representation that has extension available
    in '_review_extensions' is used for review.

    For 'source' on instance is used path from last created representation.

    Set staging directory on instance. That is probably never used because
    each created representation has it's own staging dir.
    """

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

        instance_label = instance.data["name"]
        # Create instance's staging dir in temp
        tmp_folder = tempfile.mkdtemp(prefix="traypublisher_")
        instance.data["stagingDir"] = tmp_folder
        instance.context.data["cleanupFullPaths"].append(tmp_folder)

        self.log.debug((
            "Created temp staging directory for instance {}. {}"
        ).format(instance_label, tmp_folder))

        repres = instance.data["representations"]

        creator_attributes = instance.data["creator_attributes"]
        self.log.info(json.dumps(creator_attributes))
        filepath_items = creator_attributes["filepath"]
        if not isinstance(filepath_items, list):
            filepath_items = [filepath_items]

        # Last found representation is used as source for instance
        source = None
        # Check if review is enabled and should be created
        reviewable = creator_attributes.get("reviewable")
        # Store review representation - first found that can be used for
        #   review is stored
        review_representation = None
        review_path = None

        # Make sure there are no representations with same name
        repre_names_counter = {}
        # Store created names for logging
        _repre_names = []
        # Store filepaths for validation of their existence
        source_filepaths = []

        # Create representations
        for filepath_item in filepath_items:
            filepaths = [
                os.path.join(filepath_item["directory"], filename)
                for filename in filepath_item["filenames"]
            ]
            source_filepaths.extend(filepaths)

            source = self._calculate_source(filepaths)
            filenames = filepath_item["filenames"]
            _, ext = os.path.splitext(filenames[0])
            if len(filenames) == 1:
                filenames = filenames[0]

            repre_name = repre_ext = ext[1:]
            if repre_name not in repre_names_counter:
                repre_names_counter[repre_name] = 2
            else:
                counter = repre_names_counter[repre_name]
                repre_names_counter[repre_name] += 1
                repre_name = "{}_{}".format(repre_name, counter)

            _repre_names.append('"{}"'.format(repre_name))
            representation = {
                "ext": repre_ext,
                "name": repre_name,
                "stagingDir": filepath_item["directory"],
                "files": filenames,
                "tags": []
            }
            repres.append(representation)

            if (
                reviewable
                and review_representation is None
                and ext in self._review_extensions
            ):
                review_representation = representation
                review_path = source

        instance.data["source"] = source
        instance.data["sourceFilepaths"] = source_filepaths

        if reviewable:
            self._prepare_review(instance, review_representation, review_path)

        self.log.debug((
            "Created Simple Settings instance \"{}\""
            " with {} representations: {}"
        ).format(instance_label, len(repres), ", ".join(_repre_names)))

    def _calculate_source(self, filepaths):
        cols, rems = clique.assemble(filepaths)
        if cols:
            source = cols[0].format("{head}{padding}{tail}")
        elif rems:
            source = rems[0]
        return source

    def _prepare_review(self, instance, review_representation, review_path):
        if not review_representation:
            self.log.warning((
                "Didn't find any representation"
                " that could be used as source for review"
            ))
            return

        if "review" not in instance.data["families"]:
            instance.data["families"].append("review")

        review_representation["tags"].append("review")
        self.log.debug("Representation {} was marked for review. {}".format(
            review_representation["name"], review_path
        ))
