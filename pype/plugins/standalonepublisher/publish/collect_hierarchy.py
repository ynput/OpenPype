import pyblish.api
import re
import os
from avalon import io


class CollectHierarchyInstance(pyblish.api.InstancePlugin):
    """Collecting hierarchy context from `parents` and `hierarchy` data
    present in `clip` family instances coming from the request json data file

    It will add `hierarchical_context` into each instance for integrate
    plugins to be able to create needed parents for the context if they
    don't exist yet
    """

    label = "Collect Hierarchy Clip"
    order = pyblish.api.CollectorOrder + 0.101
    hosts = ["standalonepublisher"]
    families = ["clip"]

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
            return {"entityType": entity_type, "entityName": value}

    def rename_with_hierarchy(self, instance):
        search_text = ""
        parent_name = self.asset_entity["name"]
        clip = instance.data["item"]
        clip_name = os.path.splitext(clip.name)[0].lower()

        if self.shot_rename_search_patterns:
            search_text += parent_name + clip_name
            self.hierarchy_data.update({"clip_name": clip_name})
            for type, pattern in self.shot_rename_search_patterns.items():
                p = re.compile(pattern)
                match = p.findall(search_text)
                if not match:
                    continue
                self.hierarchy_data[type] = match[-1]

        self.log.debug("__ hierarchy_data: {}".format(self.hierarchy_data))

        # format to new shot name
        self.shot_name = self.shot_rename_template.format(
            **self.hierarchy_data)
        instance.data["asset"] = self.shot_name
        self.log.debug("__ self.shot_name: {}".format(self.shot_name))

    def create_hierarchy(self, instance):
        parents = list()
        hierarchy = ""
        visual_hierarchy = [self.asset_entity]
        while True:
            visual_parent = io.find_one(
                {"_id": visual_hierarchy[-1]["data"]["visualParent"]}
            )
            if visual_parent:
                visual_hierarchy.append(visual_parent)
            else:
                visual_hierarchy.append(
                    instance.context.data["projectEntity"])
                break
        self.log.debug("__ visual_hierarchy: {}".format(visual_hierarchy))

        # add current selection context hierarchy from standalonepublisher
        for entity in reversed(visual_hierarchy):
            parents.append({
                "entityType": entity["data"]["entityType"],
                "entityName": entity["name"]
            })

        if self.shot_add_hierarchy:
            # fill the parents parts from presets
            for parent in self.shot_add_hierarchy["parents"]:
                if not self.shot_add_hierarchy["parents"][parent]:
                    prnt = {"entity"}
                else:
                    self.shot_add_hierarchy["parents"][parent] = self.shot_add_hierarchy[
                        "parents"][parent].format(**self.hierarchy_data)
                    prnt = self.convert_to_entity(
                        parent, self.shot_add_hierarchy["parents"][parent])
                parents.append(prnt)

            hierarchy = self.shot_add_hierarchy[
                "parents_path"].format(**self.shot_add_hierarchy["parents"])

        instance.data["hierarchy"] = hierarchy
        instance.data["parents"] = parents

        if self.shot_add_tasks:
            instance.data["tasks"] = self.shot_add_tasks
        else:
            instance.data["tasks"] = list()

        # updating hierarchy data
        self.hierarchy_data.update({
            "asset": self.shot_name,
            "task": "conform"
        })

    def process(self, instance):
        asset = instance.data["asset"]
        assets_shared = instance.context.data.get("assetsShared")
        context = instance.context
        anatomy_data = context.data["anatomyData"]

        self.shot_name = instance.data["asset"]
        self.hierarchy_data = dict(anatomy_data)
        self.asset_entity = context.data["assetEntity"]

        frame_start = instance.data["frameStart"]
        frame_end = instance.data["frameEnd"]

        if self.shot_rename_template:
            self.rename_with_hierarchy(instance)

        self.create_hierarchy(instance)

        # adding anatomyData for burnins
        instance.data["anatomyData"] = self.hierarchy_data

        label = f"{self.shot_name} ({frame_start}-{frame_end})"
        instance.data["label"] = label

        # dealing with shared attributes across instances
        # with the same asset name

        if assets_shared.get(asset):
            self.log.debug("Adding to shared assets: `{}`".format(
                asset))
            asset_shared = assets_shared.get(asset)
        else:
            asset_shared = assets_shared[asset]

        asset_shared.update({
            "asset": instance.data["asset"],
            "hierarchy": instance.data["hierarchy"],
            "parents": instance.data["parents"],
            "fps": instance.data["fps"],
            "tasks": instance.data["tasks"]
        })


class CollectHierarchyContext(pyblish.api.ContextPlugin):
    '''Collecting Hierarchy from instaces and building
    context hierarchy tree
    '''

    label = "Collect Hierarchy Context"
    order = pyblish.api.CollectorOrder + 0.102
    hosts = ["standalonepublisher"]

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

        final_context = {}
        for instance in instances:
            if 'clip' not in instance.data.get('family', ''):
                continue

            name = instance.data["asset"]

            # get handles
            handle_start = int(instance.data["handleStart"])
            handle_end = int(instance.data["handleEnd"])

            # inject assetsShared to other plates types
            assets_shared = context.data.get("assetsShared")

            if assets_shared:
                s_asset_data = assets_shared.get(name)
                if s_asset_data:
                    self.log.debug("__ s_asset_data: {}".format(s_asset_data))
                    name = instance.data["asset"] = s_asset_data["asset"]
                    instance.data["parents"] = s_asset_data["parents"]
                    instance.data["hierarchy"] = s_asset_data["hierarchy"]
                    instance.data["tasks"] = s_asset_data["tasks"]
                    instance.data["fps"] = s_asset_data["fps"]

                    # adding frame start if any on instance
                    start_frame = s_asset_data.get("startingFrame")
                    if start_frame:
                        instance.data["frameStart"] = start_frame
                        instance.data["frameEnd"] = start_frame + (
                            instance.data["clipOut"] -
                            instance.data["clipIn"])

            self.log.debug(
                "__ instance.data[parents]: {}".format(
                    instance.data["parents"]
                )
            )
            self.log.debug(
                "__ instance.data[hierarchy]: {}".format(
                    instance.data["hierarchy"]
                )
            )
            self.log.debug(
                "__ instance.data[name]: {}".format(instance.data["name"])
            )

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

            parents = instance.data.get('parents', [])
            self.log.debug("__ in_info: {}".format(in_info))

            actual = {name: in_info}

            for parent in reversed(parents):
                next_dict = {}
                parent_name = parent["entityName"]
                next_dict[parent_name] = {}
                next_dict[parent_name]["entity_type"] = parent["entityType"]
                next_dict[parent_name]["childs"] = actual
                actual = next_dict

            final_context = self.update_dict(final_context, actual)

        # adding hierarchy context to instance
        context.data["hierarchyContext"] = final_context
        self.log.debug("context.data[hierarchyContext] is: {}".format(
            context.data["hierarchyContext"]))
