# -*- coding: utf-8 -*-
from openpype.pipeline.create.creator_plugins import SubsetConvertorPlugin
from openpype.hosts.houdini.api.lib import imprint


class HoudiniLegacyConvertor(SubsetConvertorPlugin):
    identifier = "io.openpype.creators.houdini.legacy"
    family_to_id = {
        "camera": "io.openpype.creators.houdini.camera",
        "ass": "io.openpype.creators.houdini.ass",
        "imagesequence": "io.openpype.creators.houdini.imagesequence",
        "hda": "io.openpype.creators.houdini.hda",
        "pointcache": "io.openpype.creators.houdini.pointcache",
        "redshiftproxy": "io.openpype.creators.houdini.redshiftproxy",
        "redshift_rop": "io.openpype.creators.houdini.redshift_rop",
        "usd": "io.openpype.creators.houdini.usd",
        "usdrender": "io.openpype.creators.houdini.usdrender",
        "vdbcache": "io.openpype.creators.houdini.vdbcache"
    }

    def __init__(self, *args, **kwargs):
        super(HoudiniLegacyConvertor, self).__init__(*args, **kwargs)
        self.legacy_subsets = {}

    def find_instances(self):
        self.legacy_subsets = self.collection_shared_data.get(
            "houdini_cached_legacy_subsets")
        if not self.legacy_subsets:
            return
        self.add_convertor_item("Found {} incompatible subset{}.".format(
            len(self.legacy_subsets), "s" if len(self.legacy_subsets) > 1 else "")
        )

    def convert(self):
        if not self.legacy_subsets:
            return

        for family, subsets in self.legacy_subsets.items():
            if family in self.family_to_id:
                for subset in subsets:
                    data = {
                        "creator_identifier": self.family_to_id[family],
                        "instance_node": subset.path()
                    }
                    print("Converting {} to {}".format(
                        subset.path(), self.family_to_id[family]))
                    imprint(subset, data)
