from pyblish import api
import os
import re
import clique


class CollectPlates(api.InstancePlugin):
    """Collect plate representations.
    """

    # Run just before CollectSubsets
    order = api.CollectorOrder + 0.1020
    label = "Collect Plates"
    hosts = ["hiero"]
    families = ["plate"]

    def process(self, instance):
        # add to representations
        if not instance.data.get("representations"):
            instance.data["representations"] = list()

        self.main_clip = instance.data["item"]
        # get plate source attributes
        source_media = instance.data["sourceMedia"]
        source_path = instance.data["sourcePath"]
        source_first = instance.data["sourceFirst"]
        frame_start = instance.data["frameStart"]
        frame_end = instance.data["frameEnd"]
        handle_start = instance.data["handleStart"]
        handle_end = instance.data["handleEnd"]
        source_in = instance.data["sourceIn"]
        source_out = instance.data["sourceOut"]
        source_in_h = instance.data["sourceInH"]
        source_out_h = instance.data["sourceOutH"]

        # define if review media is sequence
        is_sequence = bool(not source_media.singleFile())
        self.log.debug("is_sequence: {}".format(is_sequence))

        file_dir = os.path.dirname(source_path)
        file = os.path.basename(source_path)
        ext = os.path.splitext(file)[-1]

        # detect if sequence
        if not is_sequence:
            # is video file
            files = file
        else:
            files = list()
            spliter, padding = self.detect_sequence(file)
            self.log.debug("_ spliter, padding: {}, {}".format(
                spliter, padding))
            base_name = file.split(spliter)[0]

            # define collection and calculate frame range
            collection = clique.Collection(
                base_name,
                ext,
                padding,
                set(range(
                    int(source_first + source_in_h),
                    int(source_first + source_out_h) + 1
                ))
            )
            self.log.debug("_ collection: {}".format(collection))

            real_files = os.listdir(file_dir)
            self.log.debug("_ real_files: {}".format(real_files))

            # collect frames to repre files list
            self.handle_start_exclude = list()
            self.handle_end_exclude = list()
            for findex, item in enumerate(collection):
                if item not in real_files:
                    self.log.debug("_ item: {}".format(item))
                    test_index = findex + int(source_first + source_in_h)
                    test_start = int(source_first + source_in)
                    test_end = int(source_first + source_out)
                    if (test_index < test_start):
                        self.handle_start_exclude.append(test_index)
                    elif (test_index > test_end):
                        self.handle_end_exclude.append(test_index)
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
            "frameStart": frame_start - handle_start,
            "frameEnd": frame_end + handle_end,
            "name": ext[1:],
            "ext": ext[1:]
        }

        instance.data["representations"].append(representation)
        self.version_data(instance)

        self.log.debug(
            "Added representations: {}".format(
                instance.data["representations"]))

        self.log.debug(
            "instance.data: {}".format(instance.data))

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

        handle_start = instance.data["handleStart"]
        handle_end = instance.data["handleEnd"]

        if self.handle_start_exclude:
            handle_start -= len(self.handle_start_exclude)

        if self.handle_end_exclude:
            handle_end -= len(self.handle_end_exclude)

        # add to data of representation
        version_data.update({
            "colorspace": self.main_clip.sourceMediaColourTransform(),
            "families": instance.data["families"],
            "subset": instance.data["subset"],
            "fps": instance.data["fps"],
            "handleStart": handle_start,
            "handleEnd": handle_end
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
