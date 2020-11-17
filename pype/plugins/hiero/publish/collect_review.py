from pyblish import api
import os
import re
import clique


class CollectReview(api.InstancePlugin):
    """Collect review from tags.

    Tag is expected to have metadata:
        {
            "family": "review"
            "track": "trackName"
        }
    """

    # Run just before CollectSubsets
    order = api.CollectorOrder + 0.1022
    label = "Collect Review"
    hosts = ["hiero"]
    families = ["review"]

    def process(self, instance):

        self.item = instance.data.get("reviewItem")
        self.item_data = instance.data.get("reviewItemData")
        self.log.info("review_track_item: {}".format(self.item))

        # add to representations
        if not instance.data.get("representations"):
            instance.data["representations"] = list()

        self.source = self.item.source().mediaSource()
        self.media_duration = int(self.source.duration())
        self.source_path = self.source.firstpath()
        is_sequence = bool(not self.source.singleFile())
        self.log.debug("is_sequence: {}".format(is_sequence))

        # handles
        handle_start = instance.data["handleStart"]
        handle_end = instance.data["handleEnd"]

        # source frame ranges
        self.source_in = int(self.item.sourceIn())
        self.source_out = int(self.item.sourceOut())
        self.source_in_h = int(self.source_in - handle_start)
        self.source_out_h = int(self.source_out + handle_end)

        # durations
        self.clip_duration = (self.source_out - self.source_in) + 1
        self.clip_duration_h = self.clip_duration + (handle_start + handle_end)

        # add created data to review item data
        self.item_data.update({
            "source": self.source,
            "sourcePath": self.source_path,
            "sourceIn": self.source_in,
            "sourceOut": self.source_out,
            "sourceInH": self.source_in_h,
            "sourceOutH": self.source_out_h,
            "clipDuration": self.clip_duration,
            "clipDurationH": self.clip_duration_h,
            "mediaDuration": self.media_duration
        })

        file_dir = os.path.dirname(self.source_path)
        file = os.path.basename(self.source_path)
        ext = os.path.splitext(file)[-1]

        # detect if sequence
        if not is_sequence:
            # is video file
            files = file
        else:
            files = list()
            file_info = next((f for f in self.source.fileinfos()), None)
            source_first = int(file_info.startFrame())

            self.log.debug("_ file: {}".format(file))
            spliter, padding = self.detect_sequence(file)
            self.log.debug("_ spliter, padding: {}, {}".format(
                spliter, padding))
            base_name = file.split(spliter)[0]
            collection = clique.Collection(base_name, ext, padding, set(range(
                int(source_first + self.source_in_h),
                int(source_first + self.source_out_h + 1))))
            self.log.debug("_ collection: {}".format(collection))
            real_files = os.listdir(file_dir)
            self.log.debug("_ real_files: {}".format(real_files))
            for item in collection:
                if item not in real_files:
                    self.log.debug("_ item: {}".format(item))
                    continue
                files.append(item)

        # change label
        instance.data["label"] = "{0} - ({1})".format(
            instance.data["label"], ext
        )

        self.log.debug("Instance review: {}".format(instance.data["name"]))

        # adding representation for review mov
        representation = {
            "files": files,
            "stagingDir": file_dir,
            "frameStart": self.source_in,
            "frameEnd": self.source_out,
            "frameStartFtrack": self.source_in_h,
            "frameEndFtrack": self.source_out_h,
            "step": 1,
            "fps": instance.data["fps"],
            "name": "review",
            "tags": ["review", "ftrackreview"],
            "ext": ext[1:]
        }

        if self.media_duration > self.clip_duration_h:
            self.log.debug("Media duration higher: {}".format(
                (self.media_duration - self.clip_duration_h)))
            representation.update({
                "frameStart": self.source_in_h,
                "frameEnd": self.source_out_h,
                "tags": ["_cut-bigger", "delete"]
            })
        elif self.media_duration < self.clip_duration_h:
            self.log.debug("Media duration higher: {}".format(
                (self.media_duration - self.clip_duration_h)))
            representation.update({
                "frameStart": self.source_in_h,
                "frameEnd": self.source_out_h,
                "tags": ["_cut-smaller", "delete"]
            })

        instance.data["representations"].append(representation)

        self.create_thumbnail(instance)

        self.log.debug(
            "Added representations: {}".format(
                instance.data["representations"]))

    def create_thumbnail(self, instance):
        source_file = os.path.basename(self.source_path)
        spliter, padding = self.detect_sequence(source_file)

        if spliter:
            head, ext = source_file.split(spliter)
        else:
            head, ext = os.path.splitext(source_file)

        # staging dir creation
        staging_dir = os.path.dirname(
            self.source_path)

        self.log.debug(
            "__ self.media_duration: {}".format(self.media_duration))
        self.log.debug("__ clip_duration_h: {}".format(self.clip_duration_h))

        thumb_frame = int(self.source_in + (
            (self.source_out - self.source_in) / 2))

        thumb_file = "{}thumbnail{}{}".format(head, thumb_frame, ".png")
        thumb_path = os.path.join(staging_dir, thumb_file)
        self.log.debug("__ thumb_path: {}".format(thumb_path))

        self.log.debug("__ thumb_frame: {}".format(thumb_frame))
        self.log.debug("__ sourceIn: `{}`".format(self.source_in))

        thumbnail = self.item.thumbnail(thumb_frame).save(
            thumb_path,
            format='png'
        )
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
            "colorspace": self.item.sourceMediaColourTransform(),
            "families": instance.data["families"],
            "subset": instance.data["subset"],
            "fps": instance.data["fps"]
        })
        instance.data["versionData"] = version_data

    def detect_sequence(self, file):
        """ Get identificating pater for image sequence

        Can find file.0001.ext, file.%02d.ext, file.####.ext

        Return:
            string: any matching sequence patern
            int: padding of sequnce numbering
        """
        foundall = re.findall(
            r"(#+)|(%\d+d)|(?<=[^a-zA-Z0-9])(\d+)(?=\.\w+$)", file)
        if foundall:
            found = sorted(list(set(foundall[0])))[-1]

            if "%" in found:
                padding = int(re.findall(r"\d+", found)[-1])
            else:
                padding = len(found)

            return found, padding
        else:
            return None, None
