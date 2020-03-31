import os

from pyblish import api


class CollectPlates(api.InstancePlugin):
    """Collect plates from tags.

    Tag is expected to have metadata:
        {
            "family": "plate"
            "subset": "main"
        }
    """

    # Run just before CollectSubsets
    order = api.CollectorOrder + 0.1021
    label = "Collect Plates"
    hosts = ["nukestudio"]
    families = ["clip"]

    def process(self, instance):
        # Exclude non-tagged instances.
        tagged = False
        for tag in instance.data["tags"]:
            tag_data = dict(tag["metadata"])
            family = tag_data.get("tag.family", "")
            if family.lower() == "plate":
                subset = tag_data.get("tag.subset", "Main")
                tagged = True
                break

        if not tagged:
            self.log.debug(
                "Skipping \"{}\" because its not tagged with "
                "\"plate\"".format(instance)
            )
            return
        self.log.debug("__ subset: `{}`".format(instance.data["subset"]))
        # if "audio" in instance.data["subset"]:
        #     return

        # Collect data.
        data = {}
        for key, value in instance.data.iteritems():
            data[key] = value

        self.log.debug("__ family: `{}`".format(family))
        self.log.debug("__ subset: `{}`".format(subset))

        data["family"] = family.lower()
        data["families"] = ["ftrack"] + instance.data["families"][1:]
        data["source"] = data["sourcePath"]
        data["subset"] = family + subset.title()
        data["name"] = data["subset"] + "_" + data["asset"]

        data["label"] = "{} - {} - ({})".format(
            data['asset'], data["subset"], os.path.splitext(
                data["sourcePath"])[1])

        if "review" in instance.data["families"]:
            data["label"] += " - review"

        # adding SourceResolution if Tag was present
        if instance.data.get("sourceResolution") and instance.data.get("main"):
            item = instance.data["item"]
            width = int(item.source().mediaSource().width())
            height = int(item.source().mediaSource().height())
            pixel_aspect = int(item.source().mediaSource().pixelAspect())

            self.log.info("Source Width and Height are: `{0} x {1} : {2}`".format(
                width, height, pixel_aspect))
            data.update({
                "width": width,
                "height": height,
                "pixelAspect": pixel_aspect
            })

        self.log.debug("Creating instance with name: {}".format(data["name"]))
        instance.context.create_instance(**data)


class CollectPlatesData(api.InstancePlugin):
    """Collect plates"""

    order = api.CollectorOrder + 0.48
    label = "Collect Plates Data"
    hosts = ["nukestudio"]
    families = ["plate"]

    def process(self, instance):
        import os
        if "review" in instance.data.get("track", ""):
            self.log.debug(
                "Skipping \"{}\" because its `review` track "
                "\"plate\"".format(instance)
            )
            return

        # add to representations
        if not instance.data.get("representations"):
            instance.data["representations"] = list()

        version_data = dict()
        context = instance.context
        anatomy = context.data.get("anatomy", None)
        padding = int(anatomy.templates['render']['padding'])

        name = instance.data["subset"]
        source_path = instance.data["sourcePath"]
        source_file = os.path.basename(source_path)

        # Filter out "clip" family.
        families = instance.data["families"] + [instance.data["family"]]
        families = list(set(families))
        if "clip" in families:
            families.remove("clip")
        family = families[-1]

        # staging dir creation
        staging_dir = os.path.dirname(
            source_path)

        item = instance.data["item"]

        transfer_data = [
            "handleStart", "handleEnd", "sourceIn", "sourceOut", "frameStart",
            "frameEnd", "sourceInH", "sourceOutH", "clipIn", "clipOut",
            "clipInH", "clipOutH", "asset", "track", "resolutionWidth", "resolutionHeight", "pixelAspect", "fps"
        ]

        # pass data to version
        version_data.update({k: instance.data[k] for k in transfer_data})

        # add to data of representation
        version_data.update({
            "colorspace": item.sourceMediaColourTransform(),
            "colorspaceScript": instance.context.data["colorspace"],
            "families": [f for f in families if 'ftrack' not in f],
            "subset": name,
            "fps": instance.context.data["fps"]
        })

        version = instance.data.get("version")
        if version:
            version_data.update({
                "version": version
            })

        source_first_frame = instance.data.get("sourceFirst")
        source_file_head = instance.data.get("sourceFileHead")

        if instance.data.get("isSequence", False):
            self.log.info("Is sequence of files")
            file = os.path.basename(source_file)
            ext = os.path.splitext(file)[-1][1:]
            self.log.debug("source_file_head: `{}`".format(source_file_head))
            head = source_file_head[:-1]
            start_frame = int(source_first_frame + instance.data["sourceInH"])
            duration = int(
                instance.data["sourceOutH"] - instance.data["sourceInH"])
            end_frame = start_frame + duration
            self.log.debug("start_frame: `{}`".format(start_frame))
            self.log.debug("end_frame: `{}`".format(end_frame))
            files = [file % i for i in range(start_frame, (end_frame + 1), 1)]
        else:
            self.log.info("Is single file")
            ext = os.path.splitext(source_file)[-1][1:]
            head = source_file_head
            files = source_file
            start_frame = instance.data["sourceInH"]
            end_frame = instance.data["sourceOutH"]

        mov_file = head + ".mov"
        mov_path = os.path.normpath(os.path.join(staging_dir, mov_file))
        if os.path.exists(mov_path):
            # adding mov into the representations
            self.log.debug("__ mov_path: {}".format(mov_path))
            instance.data["label"] += " - review"

            plates_mov_representation = {
                'files': mov_file,
                'stagingDir': staging_dir,
                "frameStart": 0,
                "frameEnd": instance.data["sourceOut"] - instance.data["sourceIn"] + 1,
                'step': 1,
                'fps': instance.context.data["fps"],
                'preview': True,
                'thumbnail': False,
                'name': "preview",
                'ext': "mov",
            }

            if mov_file not in source_file:
                instance.data["representations"].append(
                    plates_mov_representation)

        thumb_file = head + ".png"
        thumb_path = os.path.join(staging_dir, thumb_file)
        thumb_frame = instance.data["sourceIn"] + ((instance.data["sourceOut"] - instance.data["sourceIn"])/2)

        thumbnail = item.thumbnail(thumb_frame).save(
            thumb_path,
            format='png'
        )
        self.log.debug("__ sourceIn: `{}`".format(instance.data["sourceIn"]))
        self.log.debug("__ thumbnail: `{}`, frame: `{}`".format(thumbnail, thumb_frame))

        thumb_representation = {
            'files': thumb_file,
            'stagingDir': staging_dir,
            'name': "thumbnail",
            'thumbnail': True,
            'ext': "png"
        }
        instance.data["representations"].append(
            thumb_representation)

        # adding representation for plates
        frame_start = instance.data["frameStart"] - \
            instance.data["handleStart"]
        frame_end = instance.data["frameEnd"] + instance.data["handleEnd"]

        # exception for retimes
        if instance.data.get("retime"):
            source_in_h = instance.data["sourceInH"]
            source_in = instance.data["sourceIn"]
            source_handle_start = source_in_h - source_in
            frame_start = instance.data["frameStart"] + source_handle_start
            duration = instance.data["sourceOutH"] - instance.data["sourceInH"]
            frame_end = frame_start + duration

        plates_representation = {
            'files': files,
            'stagingDir': staging_dir,
            'name': ext,
            'ext': ext,
            "frameEnd": frame_end,
            "frameStart": "%0{}d".format(
                len(str(frame_end))) % frame_start
        }
        instance.data["representations"].append(plates_representation)

        # deal with retimed clip
        if instance.data.get("retime"):
            version_data.update({
                "retime": True,
                "speed": instance.data.get("speed", 1),
                "timewarps": instance.data.get("timeWarpNodes", []),
                "frameStart": frame_start,
                "frameEnd": frame_end,
            })

        instance.data["versionData"] = version_data

        # testing families
        family = instance.data["family"]
        families = instance.data["families"]

        # test prints version_data
        self.log.debug("__ version_data: {}".format(version_data))
        self.log.debug("__ representations: {}".format(
            instance.data["representations"]))
        self.log.debug("__ after family: {}".format(family))
        self.log.debug("__ after families: {}".format(families))
