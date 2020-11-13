from compiler.ast import flatten
from pyblish import api
from pype.hosts import hiero as phiero

# # developer reload modules
# from pprint import pformat
# from pype.hosts.hiero import lib
# reload(lib)
# reload(phiero)


class CollectInstances(api.ContextPlugin):
    """Collect all Track items selection."""

    order = api.CollectorOrder - 0.5
    label = "Collect Instances"
    hosts = ["hiero"]

    def process(self, context):
        # only return enabled track items
        track_items = phiero.get_track_items(check_enabled=True)
        # get sequence and video tracks
        sequence = context.data["activeSequence"]
        tracks = sequence.videoTracks()

        # add collection to context
        sub_track_items = self.collect_sub_track_items(tracks)

        context.data["subTrackItems"] = sub_track_items

        self.log.info(
            "Processing enabled track items: {}".format(len(track_items)))

        for _ti in track_items:
            data = dict()

            # get pype tag data
            tag_parsed_data = phiero.get_track_item_pype_data(_ti)
            # self.log.debug(pformat(tag_parsed_data))

            if tag_parsed_data.get("id") != "pyblish.avalon.instance":
                continue
            # add tag data to instance data
            data.update({
                k: v for k, v in tag_parsed_data.items()
                if k not in ("id", "applieswhole", "label")
            })

            asset = tag_parsed_data["asset"]
            subset = tag_parsed_data["subset"]

            # insert family into families
            family = tag_parsed_data["family"]
            families = tag_parsed_data["families"]
            families.insert(0, family)

            track = _ti.parent()
            source = _ti.source().mediaSource()
            source_path = source.firstpath()
            file_head = source.filenameHead()
            file_info = next((f for f in source.fileinfos()), None)
            source_first_frame = int(file_info.startFrame())

            data.update({
                "name": "{}_{}".format(asset, subset),
                "asset": asset,
                "item": _ti,
                "families": families,

                # tags
                "tags": _ti.tags(),

                # track item attributes
                "track": track.name(),

                # version data
                "versionData": {
                    "colorspace": _ti.sourceMediaColourTransform()
                },

                # source attribute
                "source": source,
                "sourcePath": source_path,
                "sourceFileHead": file_head,
                "sourceFirst": source_first_frame,
            })
            instance = context.create_instance(**data)

            self.log.info("Creating instance: {}".format(instance))

    def collect_sub_track_items(self, tracks):
        # collect all subtrack items
        sub_track_items = dict()
        for track in tracks:
            # skip all disabled tracks
            if not track.isEnabled():
                continue

            track_index = track.trackIndex()
            _sub_track_items = flatten(track.subTrackItems())

            # continue only if any subtrack items are collected
            if len(_sub_track_items) < 1:
                continue

            enabled_sti = list()
            # loop all found subtrack items and check if they are enabled
            for _sti in _sub_track_items:
                # checking if not enabled
                if not _sti.isEnabled():
                    continue
                # collect the subtrack item
                enabled_sti.append(_sti)

            # continue only if any subtrack items are collected
            if len(enabled_sti) < 1:
                continue

            # add collection of subtrackitems to dict
            sub_track_items[track_index] = enabled_sti

        return sub_track_items
