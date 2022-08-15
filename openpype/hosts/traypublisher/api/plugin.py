from openpype.lib.attribute_definitions import FileDef
from openpype.pipeline.create import (
    Creator,
    HiddenCreator,
    CreatedInstance
)

from .pipeline import (
    list_instances,
    update_instances,
    remove_instances,
    HostContext,
)

IMAGE_EXTENSIONS = [
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
VIDEO_EXTENSIONS = [
    ".3g2", ".3gp", ".amv", ".asf", ".avi", ".drc", ".f4a", ".f4b",
    ".f4p", ".f4v", ".flv", ".gif", ".gifv", ".m2v", ".m4p", ".m4v",
    ".mkv", ".mng", ".mov", ".mp2", ".mp4", ".mpe", ".mpeg", ".mpg",
    ".mpv", ".mxf", ".nsv", ".ogg", ".ogv", ".qt", ".rm", ".rmvb",
    ".roq", ".svi", ".vob", ".webm", ".wmv", ".yuv"
]
REVIEW_EXTENSIONS = IMAGE_EXTENSIONS + VIDEO_EXTENSIONS


class HiddenTrayPublishCreator(HiddenCreator):
    host_name = "traypublisher"

    def collect_instances(self):
        for instance_data in list_instances():
            creator_id = instance_data.get("creator_identifier")
            if creator_id == self.identifier:
                instance = CreatedInstance.from_existing(
                    instance_data, self
                )
                self._add_instance_to_context(instance)

    def update_instances(self, update_list):
        update_instances(update_list)

    def remove_instances(self, instances):
        remove_instances(instances)
        for instance in instances:
            self._remove_instance_from_context(instance)

    def _store_new_instance(self, new_instance):
        """Tray publisher specific method to store instance.

        Instance is stored into "workfile" of traypublisher and also add it
        to CreateContext.

        Args:
            new_instance (CreatedInstance): Instance that should be stored.
        """

        # Host implementation of storing metadata about instance
        HostContext.add_instance(new_instance.data_to_store())
        # Add instance to current context
        self._add_instance_to_context(new_instance)


class TrayPublishCreator(Creator):
    create_allow_context_change = True
    host_name = "traypublisher"

    def collect_instances(self):
        for instance_data in list_instances():
            creator_id = instance_data.get("creator_identifier")
            if creator_id == self.identifier:
                instance = CreatedInstance.from_existing(
                    instance_data, self
                )
                self._add_instance_to_context(instance)

    def update_instances(self, update_list):
        update_instances(update_list)

    def remove_instances(self, instances):
        remove_instances(instances)
        for instance in instances:
            self._remove_instance_from_context(instance)

    def _store_new_instance(self, new_instance):
        """Tray publisher specific method to store instance.

        Instance is stored into "workfile" of traypublisher and also add it
        to CreateContext.

        Args:
            new_instance (CreatedInstance): Instance that should be stored.
        """

        # Host implementation of storing metadata about instance
        HostContext.add_instance(new_instance.data_to_store())
        # Add instance to current context
        self._add_instance_to_context(new_instance)


class SettingsCreator(TrayPublishCreator):
    create_allow_context_change = True

    extensions = []

    def create(self, subset_name, data, pre_create_data):
        # Pass precreate data to creator attributes
        data["creator_attributes"] = pre_create_data
        data["settings_creator"] = True
        # Create new instance
        new_instance = CreatedInstance(self.family, subset_name, data, self)

        self._store_new_instance(new_instance)

    def get_instance_attr_defs(self):
        return [
            FileDef(
                "representation_files",
                folders=False,
                extensions=self.extensions,
                allow_sequences=self.allow_sequences,
                single_item=not self.allow_multiple_items,
                label="Representations",
            ),
            FileDef(
                "reviewable",
                folders=False,
                extensions=REVIEW_EXTENSIONS,
                allow_sequences=True,
                single_item=True,
                label="Reviewable representations",
                extensions_label="Single reviewable item"
            )
        ]

    def get_pre_create_attr_defs(self):
        # Use same attributes as for instance attrobites
        return self.get_instance_attr_defs()

    @classmethod
    def from_settings(cls, item_data):
        identifier = item_data["identifier"]
        family = item_data["family"]
        if not identifier:
            identifier = "settings_{}".format(family)
        return type(
            "{}{}".format(cls.__name__, identifier),
            (cls, ),
            {
                "family": family,
                "identifier": identifier,
                "label": item_data["label"].strip(),
                "icon": item_data["icon"],
                "description": item_data["description"],
                "detailed_description": item_data["detailed_description"],
                "extensions": item_data["extensions"],
                "allow_sequences": item_data["allow_sequences"],
                "allow_multiple_items": item_data["allow_multiple_items"],
                "default_variants": item_data["default_variants"]
            }
        )
