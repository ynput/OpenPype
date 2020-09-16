from pyblish import api
import os


class CollectReviews(api.InstancePlugin):
    """Collect review from tags.

    Tag is expected to have metadata:
        {
            "family": "review"
            "track": "trackName"
        }
    """

    # Run just before CollectSubsets
    order = api.CollectorOrder + 0.1022
    label = "Collect Reviews"
    hosts = ["nukestudio"]
    families = ["plate"]

    def process(self, instance):
        # Exclude non-tagged instances.
        tagged = False
        for tag in instance.data["tags"]:
            family = dict(tag["metadata"]).get("tag.family", "")
            if family.lower() == "review":
                tagged = True
                track = dict(tag["metadata"]).get("tag.track")
                break

        if not tagged:
            self.log.debug(
                "Skipping \"{}\" because its not tagged with "
                "\"review\"".format(instance)
            )
            return

        if not track:
            self.log.debug((
                "Skipping \"{}\" because tag is not having"
                "`track` in metadata"
            ).format(instance))
            return

        # add to representations
        if not instance.data.get("representations"):
            instance.data["representations"] = list()

        if track in instance.data["track"]:
            self.log.debug("Review will work on `subset`: {}".format(
                instance.data["subset"]))

            # change families
            instance.data["family"] = "plate"
            instance.data["families"] = ["review", "ftrack"]

            self.version_data(instance)
            self.create_thumbnail(instance)

            rev_inst = instance

        else:
            self.log.debug("Track item on plateMain")
            rev_inst = None
            for inst in instance.context[:]:
                if inst.data["track"] != track:
                    continue

                if inst.data["item"].name() != instance.data["item"].name():
                    continue

                rev_inst = inst
                break

            if rev_inst is None:
                raise RuntimeError((
                    "TrackItem from track name `{}` has to"
                    "be also selected"
                ).format(track))

            instance.data["families"].append("review")

        file_path = rev_inst.data.get("sourcePath")
        file_dir = os.path.dirname(file_path)
        file = os.path.basename(file_path)
        ext = os.path.splitext(file)[-1][1:]

        # change label
        instance.data["label"] = "{0} - {1} - ({2})".format(
            instance.data['asset'], instance.data["subset"], ext
        )

        self.log.debug("Instance review: {}".format(rev_inst.data["name"]))

        # adding representation for review mov
        representation = {
            "files": file,
            "stagingDir": file_dir,
            "frameStart": rev_inst.data.get("sourceIn"),
            "frameEnd": rev_inst.data.get("sourceOut"),
            "frameStartFtrack": rev_inst.data.get("sourceInH"),
            "frameEndFtrack": rev_inst.data.get("sourceOutH"),
            "step": 1,
            "fps": rev_inst.data.get("fps"),
            "name": "preview",
            "tags": ["preview", "ftrackreview"],
            "ext": ext
        }

        media_duration = instance.data.get("mediaDuration")
        clip_duration_h = instance.data.get("clipDurationH")

        if media_duration > clip_duration_h:
            self.log.debug("Media duration higher: {}".format(
                (media_duration - clip_duration_h)))
            representation.update({
                "frameStart": instance.data.get("sourceInH"),
                "frameEnd": instance.data.get("sourceOutH"),
                "tags": ["_cut-bigger", "delete"]
            })
        elif media_duration < clip_duration_h:
            self.log.debug("Media duration higher: {}".format(
                (media_duration - clip_duration_h)))
            representation.update({
                "frameStart": instance.data.get("sourceInH"),
                "frameEnd": instance.data.get("sourceOutH"),
                "tags": ["_cut-smaller", "delete"]
            })

        instance.data["representations"].append(representation)

        self.log.debug("Added representation: {}".format(representation))

    def create_thumbnail(self, instance):
        item = instance.data["item"]

        source_path = instance.data["sourcePath"]
        source_file = os.path.basename(source_path)
        head, ext = os.path.splitext(source_file)

        # staging dir creation
        staging_dir = os.path.dirname(
            source_path)

        thumb_file = head + ".png"
        thumb_path = os.path.join(staging_dir, thumb_file)
        self.log.debug("__ thumb_path: {}".format(thumb_path))

        thumb_frame = instance.data["sourceIn"] + (
            (instance.data["sourceOut"] - instance.data["sourceIn"]) / 2)
        self.log.debug("__ thumb_frame: {}".format(thumb_frame))
        thumbnail = item.thumbnail(thumb_frame).save(
            thumb_path,
            format='png'
        )

        self.log.debug(
            "__ sourceIn: `{}`".format(instance.data["sourceIn"]))
        self.log.debug(
            "__ thumbnail: `{}`, frame: `{}`".format(thumbnail, thumb_frame))

        self.log.debug("__ thumbnail: {}".format(thumbnail))

        thumb_representation = {
            'files': thumb_file,
            'stagingDir': staging_dir,
            'name': "thumbnail",
            'thumbnail': True,
            'ext': "png"
        }
        instance.data["representations"].append(
            thumb_representation)

    def version_data(self, instance):
        item = instance.data["item"]

        transfer_data = [
            "handleStart", "handleEnd", "sourceIn", "sourceOut",
            "frameStart", "frameEnd", "sourceInH", "sourceOutH",
            "clipIn", "clipOut", "clipInH", "clipOutH", "asset",
            "track"
        ]

        version_data = dict()
        # pass data to version
        version_data.update({k: instance.data[k] for k in transfer_data})

        if 'version' in instance.data:
            version_data["version"] = instance.data["version"]

        # add to data of representation
        version_data.update({
            "colorspace": item.sourceMediaColourTransform(),
            "families": instance.data["families"],
            "subset": instance.data["subset"],
            "fps": instance.context.data["fps"]
        })
        instance.data["versionData"] = version_data

        instance.data["source"] = instance.data["sourcePath"]
