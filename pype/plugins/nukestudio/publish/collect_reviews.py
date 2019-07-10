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
    order = api.CollectorOrder + 0.1025
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

        if track in instance.data["track"]:
            self.log.debug("Track item on the track: {}".format(
                instance.data["track"]))
            # Collect data.
            subset = ""
            data = {}
            for key, value in instance.data.iteritems():
                data[key] = value

            data["family"] = family.lower()
            data["ftrackFamily"] = "img"
            data["families"] = ["ftrack"]

            data["subset"] = family.lower() + subset.title()
            data["name"] = data["subset"] + "_" + data["asset"]

            data["label"] = "{} - {}".format(
                data['asset'], data["subset"]
            )

            data["source"] = data["sourcePath"]

            # self.log.debug("Creating instance with data: {}".format(data))
            instance.context.create_instance(**data)

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

            # add to representations
            if not instance.data.get("representations"):
                instance.data["representations"] = list()

            self.log.debug("Instance review: {}".format(rev_inst.data["name"]))

            # getting file path parameters
            file_path = rev_inst.data.get("sourcePath")
            file_dir = os.path.dirname(file_path)
            file = os.path.basename(file_path)
            ext = os.path.splitext(file)[-1][1:]

            # adding annotation to lablel
            instance.data["label"] += " + review (.{})".format(ext)
            instance.data["families"].append("review")
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

            self.log.debug("Added representation: {}".format(representation))
