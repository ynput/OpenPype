from pyblish import api
from copy import deepcopy


class CollectClipSubsets(api.InstancePlugin):
    """Collect Subsets from selected Clips, Tags, Preset."""

    order = api.CollectorOrder + 0.102
    label = "Collect Subsets"
    hosts = ["nukestudio"]
    families = ['clip']

    def process(self, instance):
        context = instance.context

        asset_name = instance.data["asset"]

        # get all subsets from tags and match them with nks_presets >
        # > looks to rules for tasks, subsets, representations
        subsets_collection = self.get_subsets_from_presets(instance)

        # iterate trough subsets and create instances
        for subset, attrs in subsets_collection.items():
            self.log.info((subset, attrs))
            # create families
            item = instance.data["item"]
            family = instance.data["family"]
            families = attrs["families"] + [str(subset)]
            task = attrs["task"]
            subset = "{0}{1}".format(
                subset,
                instance.data.get("subsetType") or "Default")
            instance_name = "{0}_{1}_{2}".format(asset_name, task, subset)
            self.log.info("Creating instance with name: {}".format(
                instance_name))

            # get handles
            handles = int(instance.data["handles"])
            handle_start = int(instance.data["handleStart"] + handles)
            handle_end = int(instance.data["handleEnd"] + handles)

            # get source frames
            source_in = int(instance.data["sourceIn"])
            source_out = int(instance.data["sourceOut"])

            # frame-ranges with handles
            source_in_h = source_in - handle_start
            source_out_h = source_out + handle_end

            # get timeline frames
            timeline_in = int(item.timelineIn())
            timeline_out = int(item.timelineOut())

            # frame-ranges with handles
            timeline_frame_start = timeline_in - handle_start
            timeline_frame_end = timeline_out + handle_end

            # creating comp frame range
            frame_start = instance.data["frameStart"] - handle_start
            frame_end = frame_start + \
                (timeline_frame_end - timeline_frame_start)

            # get sequence from context, and fps
            sequence = context.data["activeSequence"]
            fps = int(str(sequence.framerate()))

            context.create_instance(
                name=instance_name,
                subset=subset,
                asset=asset_name,
                track=instance.data.get("track"),
                item=item,
                task=task,
                sourcePath=instance.data.get("sourcePath"),
                family=family,
                families=families,
                sourceIn=source_in,
                sourceOut=source_out,
                sourceInH=source_in_h,
                sourceOutH=source_out_h,
                frameStart=frame_start,
                startFrame=frame_start,
                endFrame=frame_end,
                timelineIn=timeline_in,
                timelineOut=timeline_out,
                timelineInHandles=timeline_frame_start,
                timelineOutHandles=timeline_frame_end,
                fps=fps,
                handles=instance.data["handles"],
                handleStart=handle_start,
                handleEnd=handle_end,
                attributes=attrs,
                version=instance.data["version"],
                hierarchy=instance.data.get("hierarchy", None),
                parents=instance.data.get("parents", None),
                publish=True
            )

        # removing original instance
        context.remove(instance)

    def get_subsets_from_presets(self, instance):

        family = instance.data["family"]
        # get presets and tags
        tag_tasks = instance.data["tasks"]
        presets = instance.context.data['presets']
        nks_presets = presets[instance.context.data['host']]
        family_default_preset = nks_presets["asset_default"].get(family)

        if family_default_preset:
            frame_start = family_default_preset.get("fstart", 1)
            instance.data["frameStart"] = int(frame_start)

        # get specific presets
        pr_host_tasks = deepcopy(
            nks_presets["rules_tasks"]).get("hostTasks", None)
        pr_host_subsets = deepcopy(
            nks_presets["rules_tasks"]).get("hostSubsets", None)

        subsets_collect = dict()
        # iterate tags and collect subset properities from presets
        for task in tag_tasks:
            try:
                # get host for task
                host = None
                host = [h for h, tasks in pr_host_tasks.items()
                        if task in tasks][0]
            except IndexError:
                pass

            try:
                # get subsets for task
                subsets = None
                subsets = pr_host_subsets[host]
            except KeyError:
                pass

            if not subsets:
                continue

            # get subsets for task
            for sub in subsets:
                # get specific presets
                pr_subsets = deepcopy(nks_presets["rules_subsets"])
                pr_representations = deepcopy(
                    nks_presets["rules_representations"])

                # initialise collection dictionary
                subs_data = dict()

                # gets subset properities
                subs_data[sub] = None
                subs_data[sub] = pr_subsets.get(sub, None)

                # gets representation if in keys
                if subs_data[sub] and (
                    "representation" in subs_data[sub].keys()
                ):
                    repr_name = subs_data[sub]["representation"]

                    # owerwrite representation key with values from preset
                    subs_data[sub]["representation"] = pr_representations[
                        repr_name
                    ]
                    subs_data[sub]["representation"]["name"] = repr_name

                # gets nodes and presets data if in keys
                # gets nodes if any
                if subs_data[sub] and (
                    "nodes" in subs_data[sub].keys()
                ):
                    # iterate trough each node
                    for k in subs_data[sub]["nodes"]:
                        pr_node = k
                        pr_family = subs_data[sub]["nodes"][k]["family"]

                        # create attribute dict for later filling
                        subs_data[sub]["nodes"][k]["attributes"] = dict()

                        # iterate presets for the node
                        for p, path in subs_data[sub]["nodes"][k][
                                "presets"].items():

                            # adds node type and family for preset path
                            nPath = path + [pr_node, pr_family]

                            # create basic iternode to be wolked trough until
                            # found presets at the end
                            iternode = presets[p]
                            for part in nPath:
                                iternode = iternode[part]

                            iternode = {k: v for k, v in iternode.items()
                                        if not k.startswith("_")}
                            # adds found preset to attributes of the node
                            subs_data[sub]["nodes"][k][
                                "attributes"].update(iternode)

                        # removes preset key
                        subs_data[sub]["nodes"][k].pop("presets")

                # add all into dictionary
                subs_data[sub]["task"] = task.lower()
                subsets_collect.update(subs_data)

        return subsets_collect
