# -*- coding: utf-8 -*-
"""Converter for legacy Houdini subsets."""
from openpype.pipeline.create.creator_plugins import SubsetConvertorPlugin
from openpype.hosts.houdini.api.lib import imprint


class HoudiniLegacyConvertor(SubsetConvertorPlugin):
    """Find and convert any legacy subsets in the scene.

    This Converter will find all legacy subsets in the scene and will
    transform them to the current system. Since the old subsets doesn't
    retain any information about their original creators, the only mapping
    we can do is based on their families.

    Its limitation is that you can have multiple creators creating subset
    of the same family and there is no way to handle it. This code should
    nevertheless cover all creators that came with OpenPype.

    """
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
        """Find legacy subsets in the scene.

        Legacy subsets are the ones that doesn't have `creator_identifier`
        parameter on them.

        This is using cached entries done in
        :py:meth:`~HoudiniCreatorBase.cache_subsets()`

        """
        self.legacy_subsets = self.collection_shared_data.get(
            "houdini_cached_legacy_subsets")
        if not self.legacy_subsets:
            return
        self.add_convertor_item("Found {} incompatible subset{}.".format(
            len(self.legacy_subsets), "s" if len(self.legacy_subsets) > 1 else "")
        )

    def convert(self):
        """Convert all legacy subsets to current.

        It is enough to add `creator_identifier` and `instance_node`.

        """
        if not self.legacy_subsets:
            return

        for family, subsets in self.legacy_subsets.items():
            if family in self.family_to_id:
                for subset in subsets:
                    data = {
                        "creator_identifier": self.family_to_id[family],
                        "instance_node": subset.path()
                    }
                    if family == "pointcache":
                        data["families"] = ["abc"]
                    self.log.info("Converting {} to {}".format(
                        subset.path(), self.family_to_id[family]))
                    imprint(subset, data)
