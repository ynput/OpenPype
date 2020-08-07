import os
import pyblish.api


class CollectInstancesFromJson(pyblish.api.ContextPlugin):
    """
    Collecting temp json data sent from a host context
    and path for returning json data back to hostself.

    Setting avalon session into correct context

    Args:
        context (obj): pyblish context session

    """

    label = "Collect instances from JSON"
    order = pyblish.api.CollectorOrder - 0.48

    def process(self, context):

        _S = context.data["avalonSession"]
        asset = _S["AVALON_ASSET"]
        task = _S["AVALON_TASK"]
        host = _S["AVALON_APP"]

        json_data = context.data.get("jsonData", None)
        assert json_data, "No `json_data` data in json file"

        instances_data = json_data.get("instances", None)
        assert instances_data, "No `instance` data in json file"

        staging_dir = json_data.get("stagingDir", None)
        assert staging_dir, "No `stagingDir` path in json file"

        host = context.data["host"]
        presets = context.data["presets"][host]

        rules_tasks = presets["rules_tasks"]

        asset_default = presets["asset_default"]
        assert asset_default, ("No `asset_default` data in"
                               "`/presets/[host]/asset_default.json` file")

        # get frame start > first try from asset data
        frame_start = context.data["assetData"].get("frameStart", None)
        if not frame_start:
            self.log.debug("frame_start not on any parent entity")
            # get frame start > third try from parent data
            frame_start = asset_default["frameStart"]

        assert frame_start, "No `frame_start` data found, "
        "please set `fstart` on asset"
        self.log.debug("frame_start: `{}`".format(frame_start))

        # get handles > first try from asset data
        handle_start = context.data["assetData"].get("handleStart", None)
        handle_end = context.data["assetData"].get("handleEnd", None)
        if (handle_start is None) or (handle_end is None):
            # get frame start > second try from parent data
            handle_start = asset_default.get("handleStart", None)
            handle_end = asset_default.get("handleEnd", None)

        assert (
            (handle_start is not None) or (
                handle_end is not None)), (
                    "No `handle_start, handle_end` data found")

        instances = []

        current_file = os.path.basename(context.data.get("currentFile"))
        name, ext = os.path.splitext(current_file)

        # get current file host
        family = "workfile"
        subset_name = "{0}{1}".format(task, 'Default')
        instance_name = "{0}_{1}_{2}".format(name,
                                             family,
                                             subset_name)
        # Set label
        label = "{0} - {1}".format(name, task)

        # get project file instance Data
        wf_instance = next((inst for inst in instances_data
                            if inst.get("family", None) in 'workfile'), None)

        if wf_instance:
            self.log.debug('wf_instance: {}'.format(wf_instance))

            version = int(wf_instance.get("version", None))
            # get working file into instance for publishing
            instance = context.create_instance(instance_name)
            instance.data.update(wf_instance)

            instance.data.update({
                "subset": subset_name,
                "stagingDir": staging_dir,
                "task": task,
                "representations": [{
                    "files": current_file,
                    'stagingDir': staging_dir,
                    'name': "projectfile",
                    'ext': ext[1:]
                }],
                "host": host,
                "asset": asset,
                "label": label,
                "name": name,
                "family": family,
                "families": ["ftrack"],
                "publish": True,
                "version": version
            })
            instances.append(instance)

        for inst in instances_data:
            # for key, value in inst.items():
            #     self.log.debug('instance[key]: {}'.format(key))
            #
            version = int(inst.get("version", None))
            assert version, "No `version` string in json file"

            name = asset = inst.get("name", None)
            assert name, "No `name` key in json_data.instance: {}".format(inst)

            family = inst.get("family", None)
            assert family, "No `family` key in json_data.instance: {}".format(
                inst)

            if family in 'workfile':
                continue

            files_list = inst.get("files", None)
            assert files_list, "`files` are empty in json file"

            hierarchy = inst.get("hierarchy", None)
            assert hierarchy, f"No `hierarchy` data in json file for {name}"

            parents = inst.get("parents", None)
            assert parents, "No `parents` data in json file"

            tags = inst.get("tags", None)
            if tags:
                tasks = [t["task"] for t in tags
                         if t.get("task")]
            else:
                tasks = rules_tasks["defaultTasks"]
            self.log.debug("tasks: `{}`".format(tasks))

            subset_lst = []
            subset_dict = {}
            for task in tasks:
                # create list of tasks for creation
                if not inst.get('tasks', None):
                    inst['tasks'] = list()

                # append taks into list for later hierarchy cration
                if task not in inst['tasks']:
                    inst['tasks'].append(task)

                subsets = rules_tasks["taskToSubsets"][task]
                for sub in subsets:
                    self.log.debug(sub)
                    try:
                        isinstance(subset_dict[sub], list)
                    except Exception:
                        subset_dict[sub] = list()

                    subset_dict[sub].append(task)

                subset_lst.extend([s for s in subsets if s not in subset_lst])

            for subset in subset_lst:
                if inst["subsetToRepresentations"].get(subset, None):
                    repr = inst["subsetToRepresentations"][subset]
                    ext = repr['representation']
                else:
                    continue
                family = inst["family"]
                # skip if thumnail in name of subset
                if "thumbnail" in subset:
                    continue
                elif "audio" in subset:
                    family = subset
                    subset_name = "{0}{1}".format(subset, "Main")
                elif "reference" in subset:
                    family = "review"
                    subset_name = "{0}{1}".format(family, "Reference")
                else:
                    subset_name = "{0}{1}".format(subset, 'Default')

                # create unique subset's name
                name = "{0}_{1}_{2}".format(asset,
                                            inst["family"],
                                            subset_name)

                instance = context.create_instance(name)
                files = [f for f in files_list
                         if subset in f or "thumbnail" in f]

                instance.data.update({
                    "subset": subset_name,
                    "stagingDir": staging_dir,
                    "tasks": subset_dict[subset],
                    "frameStart": frame_start,
                    "handleStart": handle_start,
                    "handleEnd": handle_end,
                    "asset": asset,
                    "hierarchy": hierarchy,
                    "parents": parents,
                    "files": files,
                    "label": "{0} - {1}".format(
                        asset, subset_name),
                    "name": name,
                    "family": family,
                    "families": [subset, inst["family"], 'ftrack'],
                    "jsonData": inst,
                    "jsonReprSubset": subset,
                    "jsonReprExt": ext,
                    "publish": True,
                    "version": version})
                self.log.info(
                    "collected instance: {}".format(instance.data))
                instances.append(instance)

        context.data["instances"] = instances

        self.log.debug("context: {}".format(context))

    def sort_by_task(self, instance):
        """Sort by family"""
        return instance.data.get("task", instance.data.get("task"))
