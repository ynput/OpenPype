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
    families = ["clip"]

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
            self.log.debug(
                "Skipping \"{}\" because tag is not having `track` in metadata".format(instance)
            )
            return

        # add to representations
        if not instance.data.get("representations"):
            instance.data["representations"] = list()

        if track in instance.data["track"]:
            self.log.debug("Review will work on `subset`: {}".format(
                instance.data["subset"]))

            # change families
            instance.data["family"] = "review"
            instance.data["families"] = ["review", "ftrack"]

            self.version_data(instance)
            self.create_thumbnail(instance)

            rev_inst = instance

        else:
            self.log.debug("Track item on plateMain")
            rev_inst = None
            for inst in instance.context[:]:
                if inst.data["track"] in track:
                    rev_inst = inst
                    self.log.debug("Instance review: {}".format(
                        rev_inst.data["name"]))

            if rev_inst is None:
                raise RuntimeError(
                    "TrackItem from track name `{}` has to be also selected".format(
                        track)
                )

            # change families
            instance.data["label"] += " + review (.{})".format(ext)
            instance.data["families"].append("review")

        file_path = rev_inst.data.get("sourcePath")
        file_dir = os.path.dirname(file_path)
        file = os.path.basename(file_path)
        ext = os.path.splitext(file)[-1][1:]

        instance.data["label"] += " + review (.{})".format(ext)

        self.log.debug("Instance review: {}".format(rev_inst.data["name"]))


        # adding representation for review mov
        representation = {
            "files": file,
            "stagingDir": file_dir,
            "startFrame": rev_inst.data.get("sourceIn"),
            "endFrame": rev_inst.data.get("sourceOut"),
            "step": 1,
            "frameRate": rev_inst.data.get("fps"),
            "preview": True,
            "thumbnail": False,
            "name": "preview",
            "ext": ext
        }
        instance.data["representations"].append(representation)

        self.log.debug("_ `family`: {}".format(
            instance.data["family"]))
        self.log.debug("_ `families`: {}".format(
            instance.data["families"]))
        self.log.debug("_ `instance.data`: {}".format(
            instance.data))
        self.log.debug("_ `representations`: {}".format(
            instance.data["representations"]))

        self.log.debug("Added representation: {}".format(representation))

    def create_thumbnail(self, instance):
        item = instance.data["item"]
        source_in = instance.data["sourceIn"]

        source_path = instance.data["sourcePath"]
        source_file = os.path.basename(source_path)
        head, ext = os.path.splitext(source_file)

        # staging dir creation
        staging_dir = os.path.dirname(
            source_path)

        thumb_file = head + ".png"
        thumb_path = os.path.join(staging_dir, thumb_file)
        self.log.debug("__ thumb_path: {}".format(thumb_path))
        self.log.debug("__ source_in: {}".format(source_in))
        thumbnail = item.thumbnail(source_in).save(
            thumb_path,
            format='png'
        )
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
        name = instance.data["subset"]
        asset = instance.data["asset"]
        track = instance.data["track"]
        version = instance.data["version"]
        item = instance.data["item"]

        # get handles
        handle_start = int(instance.data["handleStart"])
        handle_end = int(instance.data["handleEnd"])

        # get source frames
        source_in = int(instance.data["sourceIn"])
        source_out = int(instance.data["sourceOut"])


        # get source frames
        frame_start = instance.data.get("frameStart", 1)
        frame_end = frame_start + (source_out - source_in)

        # get source frames
        instance.data["sourceInH"] = source_in - handle_start
        instance.data["sourceOutH"] = source_out + handle_end

        # get timeline frames
        timeline_in = int(item.timelineIn())
        timeline_out = int(item.timelineOut())

        # frame-ranges with handles
        timeline_frame_start = timeline_in - handle_start
        timeline_frame_end = timeline_out + handle_end

        # get colorspace
        colorspace = item.sourceMediaColourTransform()

        # get sequence from context, and fps
        fps = instance.data["fps"]

        version_data = dict()
        version_data.update({
            "handles": handle_start,
            "handleStart": handle_start,
            "handleEnd": handle_end,
            "sourceIn": source_in,
            "sourceOut": source_out,
            "startFrame": frame_start,
            "endFrame": frame_end,
            "timelineIn": timeline_in,
            "timelineOut": timeline_out,
            "timelineInHandles": timeline_frame_start,
            "timelineOutHandles": timeline_frame_end,
            "fps": fps,
            "colorspace": colorspace,
            "families": instance.data["families"],
            "asset": asset,
            "subset": name,
            "track": track,
            "version": int(version)
        })
        instance.data["versionData"] = version_data
        instance.data["source"] = instance.data["sourcePath"]
