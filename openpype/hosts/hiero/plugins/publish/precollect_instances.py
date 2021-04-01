from compiler.ast import flatten
from pyblish import api
from openpype.hosts.hiero import api as phiero
import hiero
# from openpype.hosts.hiero.api import lib
# reload(lib)
# reload(phiero)


class PreCollectInstances(api.ContextPlugin):
    """Collect all Track items selection."""

    order = api.CollectorOrder - 0.509
    label = "Pre-collect Instances"
    hosts = ["hiero"]

    def process(self, context):
        track_items = phiero.get_track_items(
            selected=True, check_tagged=True, check_enabled=True)
        # only return enabled track items
        if not track_items:
            track_items = phiero.get_track_items(
                check_enabled=True, check_tagged=True)
        # get sequence and video tracks
        sequence = context.data["activeSequence"]
        tracks = sequence.videoTracks()

        # add collection to context
        tracks_effect_items = self.collect_sub_track_items(tracks)

        context.data["tracksEffectItems"] = tracks_effect_items

        self.log.info(
            "Processing enabled track items: {}".format(len(track_items)))

        for _ti in track_items:
            data = dict()
            clip = _ti.source()

            # get clips subtracks and anotations
            annotations = self.clip_annotations(clip)
            subtracks = self.clip_subtrack(_ti)
            self.log.debug("Annotations: {}".format(annotations))
            self.log.debug(">> Subtracks: {}".format(subtracks))

            # get pype tag data
            tag_parsed_data = phiero.get_track_item_pype_data(_ti)
            # self.log.debug(pformat(tag_parsed_data))

            if not tag_parsed_data:
                continue

            if tag_parsed_data.get("id") != "pyblish.avalon.instance":
                continue
            # add tag data to instance data
            data.update({
                k: v for k, v in tag_parsed_data.items()
                if k not in ("id", "applieswhole", "label")
            })

            asset = tag_parsed_data["asset"]
            subset = tag_parsed_data["subset"]
            review = tag_parsed_data.get("review")
            audio = tag_parsed_data.get("audio")

            # remove audio attribute from data
            data.pop("audio")

            # insert family into families
            family = tag_parsed_data["family"]
            families = [str(f) for f in tag_parsed_data["families"]]
            families.insert(0, str(family))

            track = _ti.parent()
            media_source = _ti.source().mediaSource()
            source_path = media_source.firstpath()
            file_head = media_source.filenameHead()
            file_info = media_source.fileinfos().pop()
            source_first_frame = int(file_info.startFrame())

            # apply only for feview and master track instance
            if review:
                families += ["review", "ftrack"]

            data.update({
                "name": "{} {} {}".format(asset, subset, families),
                "asset": asset,
                "item": _ti,
                "families": families,

                # tags
                "tags": _ti.tags(),

                # track item attributes
                "track": track.name(),
                "trackItem": track,

                # version data
                "versionData": {
                    "colorspace": _ti.sourceMediaColourTransform()
                },

                # source attribute
                "source": source_path,
                "sourceMedia": media_source,
                "sourcePath": source_path,
                "sourceFileHead": file_head,
                "sourceFirst": source_first_frame,

                # clip's effect
                "clipEffectItems": subtracks
            })

            instance = context.create_instance(**data)

            self.log.info("Creating instance: {}".format(instance))

            if audio:
                a_data = dict()

                # add tag data to instance data
                a_data.update({
                    k: v for k, v in tag_parsed_data.items()
                    if k not in ("id", "applieswhole", "label")
                })

                # create main attributes
                subset = "audioMain"
                family = "audio"
                families = ["clip", "ftrack"]
                families.insert(0, str(family))

                name = "{} {} {}".format(asset, subset, families)

                a_data.update({
                    "name": name,
                    "subset": subset,
                    "asset": asset,
                    "family": family,
                    "families": families,
                    "item": _ti,

                    # tags
                    "tags": _ti.tags(),
                })

                a_instance = context.create_instance(**a_data)
                self.log.info("Creating audio instance: {}".format(a_instance))

    @staticmethod
    def clip_annotations(clip):
        """
        Returns list of Clip's hiero.core.Annotation
        """
        annotations = []
        subTrackItems = flatten(clip.subTrackItems())
        annotations += [item for item in subTrackItems if isinstance(
            item, hiero.core.Annotation)]
        return annotations

    @staticmethod
    def clip_subtrack(clip):
        """
        Returns list of Clip's hiero.core.SubTrackItem
        """
        subtracks = []
        subTrackItems = flatten(clip.parent().subTrackItems())
        for item in subTrackItems:
            # avoid all anotation
            if isinstance(item, hiero.core.Annotation):
                continue
            # # avoid all not anaibled
            if not item.isEnabled():
                continue
            subtracks.append(item)
        return subtracks

    @staticmethod
    def collect_sub_track_items(tracks):
        """
        Returns dictionary with track index as key and list of subtracks
        """
        # collect all subtrack items
        sub_track_items = dict()
        for track in tracks:
            items = track.items()

            # skip if no clips on track > need track with effect only
            if items:
                continue

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
                if isinstance(_sti, hiero.core.Annotation):
                    continue
                # collect the subtrack item
                enabled_sti.append(_sti)

            # continue only if any subtrack items are collected
            if len(enabled_sti) < 1:
                continue

            # add collection of subtrackitems to dict
            sub_track_items[track_index] = enabled_sti

        return sub_track_items
