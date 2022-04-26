import os
import re
from copy import deepcopy
import pyblish.api

from openpype.pipeline import legacy_io


class CollectHierarchyInstance(pyblish.api.ContextPlugin):
    """Collecting hierarchy context from `parents` and `hierarchy` data
    present in `clip` family instances coming from the request json data file

    It will add `hierarchical_context` into each instance for integrate
    plugins to be able to create needed parents for the context if they
    don't exist yet
    """

    label = "Collect Hierarchy Clip"
    order = pyblish.api.CollectorOrder + 0.101
    hosts = ["standalonepublisher"]
    families = ["shot"]

    # presets
    shot_rename_template = None
    shot_rename_search_patterns = None
    shot_add_hierarchy = None
    shot_add_tasks = None

    def convert_to_entity(self, key, value):
        # ftrack compatible entity types
        types = {"shot": "Shot",
                 "folder": "Folder",
                 "episode": "Episode",
                 "sequence": "Sequence",
                 "track": "Sequence",
                 }
        # convert to entity type
        entity_type = types.get(key, None)

        # return if any
        if entity_type:
            return {"entity_type": entity_type, "entity_name": value}

    def rename_with_hierarchy(self, instance):
        search_text = ""
        parent_name = instance.context.data["assetEntity"]["name"]
        clip = instance.data["item"]
        clip_name = os.path.splitext(clip.name)[0].lower()
        if self.shot_rename_search_patterns:
            search_text += parent_name + clip_name
            instance.data["anatomyData"].update({"clip_name": clip_name})
            for type, pattern in self.shot_rename_search_patterns.items():
                p = re.compile(pattern)
                match = p.findall(search_text)
                if not match:
                    continue
                instance.data["anatomyData"][type] = match[-1]

        # format to new shot name
        instance.data["asset"] = self.shot_rename_template.format(
            **instance.data["anatomyData"])

    def create_hierarchy(self, instance):
        parents = list()
        hierarchy = list()
        visual_hierarchy = [instance.context.data["assetEntity"]]
        while True:
            visual_parent = legacy_io.find_one(
                {"_id": visual_hierarchy[-1]["data"]["visualParent"]}
            )
            if visual_parent:
                visual_hierarchy.append(visual_parent)
            else:
                visual_hierarchy.append(
                    instance.context.data["projectEntity"])
                break

        # add current selection context hierarchy from standalonepublisher
        for entity in reversed(visual_hierarchy):
            parents.append({
                "entity_type": entity["data"]["entityType"],
                "entity_name": entity["name"]
            })

        if self.shot_add_hierarchy:
            parent_template_patern = re.compile(r"\{([a-z]*?)\}")
            # fill the parents parts from presets
            shot_add_hierarchy = self.shot_add_hierarchy.copy()
            hierarchy_parents = shot_add_hierarchy["parents"].copy()

            # fill parent keys data template from anatomy data
            for parent_key in hierarchy_parents:
                hierarchy_parents[parent_key] = hierarchy_parents[
                    parent_key].format(**instance.data["anatomyData"])

            for _index, _parent in enumerate(
                    shot_add_hierarchy["parents_path"].split("/")):
                parent_filled = _parent.format(**hierarchy_parents)
                parent_key = parent_template_patern.findall(_parent).pop()

                # in case SP context is set to the same folder
                if (_index == 0) and ("folder" in parent_key) \
                        and (parents[-1]["entity_name"] == parent_filled):
                    self.log.debug(f" skipping : {parent_filled}")
                    continue

                # in case first parent is project then start parents from start
                if (_index == 0) and ("project" in parent_key):
                    self.log.debug("rebuilding parents from scratch")
                    project_parent = parents[0]
                    parents = [project_parent]
                    self.log.debug(f"project_parent: {project_parent}")
                    self.log.debug(f"parents: {parents}")
                    continue

                prnt = self.convert_to_entity(
                    parent_key, parent_filled)
                parents.append(prnt)
                hierarchy.append(parent_filled)

        # convert hierarchy to string
        hierarchy = "/".join(hierarchy)

        # assign to instance data
        instance.data["hierarchy"] = hierarchy
        instance.data["parents"] = parents

        # print
        self.log.debug(f"Hierarchy: {hierarchy}")
        self.log.debug(f"parents: {parents}")

        if self.shot_add_tasks:
            tasks_to_add = dict()
            project_doc = legacy_io.find_one({"type": "project"})
            project_tasks = project_doc["config"]["tasks"]
            for task_name, task_data in self.shot_add_tasks.items():
                _task_data = deepcopy(task_data)

                # fixing enumerator from settings
                _task_data["type"] = task_data["type"][0]

                # check if task type in project task types
                if _task_data["type"] in project_tasks.keys():
                    tasks_to_add.update({task_name: _task_data})
                else:
                    raise KeyError(
                        "Wrong FtrackTaskType `{}` for `{}` is not"
                        " existing in `{}``".format(
                            _task_data["type"],
                            task_name,
                            list(project_tasks.keys())))

            instance.data["tasks"] = tasks_to_add
        else:
            instance.data["tasks"] = dict()

        # updating hierarchy data
        instance.data["anatomyData"].update({
            "asset": instance.data["asset"],
            "task": "conform"
        })

    def process(self, context):
        for instance in context:
            if instance.data["family"] in self.families:
                self.processing_instance(instance)

    def processing_instance(self, instance):
        self.log.info(f"_ instance: {instance}")
        # adding anatomyData for burnins
        instance.data["anatomyData"] = deepcopy(
            instance.context.data["anatomyData"])

        asset = instance.data["asset"]
        assets_shared = instance.context.data.get("assetsShared")

        frame_start = instance.data["frameStart"]
        frame_end = instance.data["frameEnd"]

        if self.shot_rename_template:
            self.rename_with_hierarchy(instance)

        self.create_hierarchy(instance)

        shot_name = instance.data["asset"]
        self.log.debug(f"Shot Name: {shot_name}")

        label = f"{shot_name} ({frame_start}-{frame_end})"
        instance.data["label"] = label

        # dealing with shared attributes across instances
        # with the same asset name
        if assets_shared.get(asset):
            asset_shared = assets_shared.get(asset)
        else:
            asset_shared = assets_shared[asset]

        asset_shared.update({
            "asset": instance.data["asset"],
            "hierarchy": instance.data["hierarchy"],
            "parents": instance.data["parents"],
            "tasks": instance.data["tasks"],
            "anatomyData": instance.data["anatomyData"]
        })


class CollectHierarchyContext(pyblish.api.ContextPlugin):
    '''Collecting Hierarchy from instances and building
    context hierarchy tree
    '''

    label = "Collect Hierarchy Context"
    order = pyblish.api.CollectorOrder + 0.102
    hosts = ["standalonepublisher"]
    families = ["shot"]

    def update_dict(self, ex_dict, new_dict):
        for key in ex_dict:
            if key in new_dict and isinstance(ex_dict[key], dict):
                new_dict[key] = self.update_dict(ex_dict[key], new_dict[key])
            else:
                if ex_dict.get(key) and new_dict.get(key):
                    continue
                else:
                    new_dict[key] = ex_dict[key]

        return new_dict

    def process(self, context):
        instances = context
        # create hierarchyContext attr if context has none
        assets_shared = context.data.get("assetsShared")
        final_context = {}
        for instance in instances:
            if 'editorial' in instance.data.get('family', ''):
                continue
            # inject assetsShared to other instances with
            # the same `assetShareName` attribute in data
            asset_shared_name = instance.data.get("assetShareName")

            s_asset_data = assets_shared.get(asset_shared_name)
            if s_asset_data:
                instance.data["asset"] = s_asset_data["asset"]
                instance.data["parents"] = s_asset_data["parents"]
                instance.data["hierarchy"] = s_asset_data["hierarchy"]
                instance.data["tasks"] = s_asset_data["tasks"]
                instance.data["anatomyData"] = s_asset_data["anatomyData"]

            # generate hierarchy data only on shot instances
            if 'shot' not in instance.data.get('family', ''):
                continue

            name = instance.data["asset"]

            # get handles
            handle_start = int(instance.data["handleStart"])
            handle_end = int(instance.data["handleEnd"])

            in_info = {}

            # suppose that all instances are Shots
            in_info['entity_type'] = 'Shot'

            # get custom attributes of the shot

            in_info['custom_attributes'] = {
                "handleStart": handle_start,
                "handleEnd": handle_end,
                "frameStart": instance.data["frameStart"],
                "frameEnd": instance.data["frameEnd"],
                "clipIn": instance.data["clipIn"],
                "clipOut": instance.data["clipOut"],
                'fps': instance.data["fps"]
            }

            in_info['tasks'] = instance.data['tasks']

            from pprint import pformat
            parents = instance.data.get('parents', [])
            self.log.debug(f"parents: {pformat(parents)}")

            actual = {name: in_info}

            for parent in reversed(parents):
                next_dict = {}
                parent_name = parent["entity_name"]
                next_dict[parent_name] = {}
                next_dict[parent_name]["entity_type"] = parent["entity_type"]
                next_dict[parent_name]["childs"] = actual
                actual = next_dict

            final_context = self.update_dict(final_context, actual)

        # adding hierarchy context to instance
        context.data["hierarchyContext"] = final_context
        self.log.debug(f"hierarchyContext: {pformat(final_context)}")
        self.log.info("Hierarchy instance collected")
