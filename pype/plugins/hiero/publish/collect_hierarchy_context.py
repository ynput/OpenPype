import pyblish.api
import avalon.api as avalon
import re


class CollectHierarchyInstance(pyblish.api.InstancePlugin):
    """Collecting hierarchy context from `parents` and `hierarchy` data
    present in `clip` family instances coming from the request json data file

    It will add `hierarchical_context` into each instance for integrate
    plugins to be able to create needed parents for the context if they
    don't exist yet
    """

    label = "Collect Hierarchy Clip"
    order = pyblish.api.CollectorOrder
    families = ["clip"]

    def process(self, instance):

        assets_shared = instance.context.data.get("assetsShared")
        asset = instance.data["asset"]
        resolution_width = instance.data["resolutionWidth"]
        resolution_height = instance.data["resolutionHeight"]
        pixel_aspect = instance.data["pixelAspect"]
        clip_in = instance.data["clipIn"]
        clip_out = instance.data["clipOut"]
        fps = instance.context.data["fps"]

        # create new shot asset name
        asset = instance.data["asset"]

        # add formated hierarchy path into instance data
        hierarchy = instance.data["hierarchy"]
        parents = instance.data["parents"]

        tasks = instance.data.get("tasks")

        self.log.info(
            "clip: {asset}[{clip_in}:{clip_out}]".format(
                **locals()))

        shared_data = assets_shared.get(asset)

        if not shared_data:
            shared_data = dict()
            assets_shared[asset] = shared_data

        shared_data.update({
            "asset": asset,
            "hierarchy": hierarchy,
            "parents": parents,
            "resolutionWidth": resolution_width,
            "resolutionHeight": resolution_height,
            "pixelAspect": pixel_aspect,
            "fps": fps,
            "tasks": tasks or []
        })

        self.log.debug(
            "assets_shared: {}".format(assets_shared))


class CollectHierarchyContext(pyblish.api.ContextPlugin):
    '''Collecting Hierarchy from instaces and building
    context hierarchy tree
    '''

    label = "Collect Hierarchy Context"
    order = pyblish.api.CollectorOrder + 0.103

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
        instances = context[:]

        # create hierarchyContext attr if context has none

        temp_context = {}
        for instance in instances:
            if 'workfile' in instance.data.get('family', ''):
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
                    instance.data["resolutionWidth"] = s_asset_data[
                        "resolutionWidth"]
                    instance.data["resolutionHeight"] = s_asset_data[
                        "resolutionHeight"]
                    instance.data["pixelAspect"] = s_asset_data["pixelAspect"]
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

            in_info["inputs"] = [
                x["_id"] for x in instance.data.get("assetbuilds", [])
            ]

            # suppose that all instances are Shots
            in_info['entity_type'] = 'Shot'

            # get custom attributes of the shot
            if instance.data.get("main"):
                in_info['custom_attributes'] = {
                    "handleStart": handle_start,
                    "handleEnd": handle_end,
                    "frameStart": instance.data["frameStart"],
                    "frameEnd": instance.data["frameEnd"],
                    "clipIn": instance.data["clipIn"],
                    "clipOut": instance.data["clipOut"],
                    'fps': instance.context.data["fps"]
                }

                # adding SourceResolution if Tag was present
                if instance.data.get("main"):
                    in_info['custom_attributes'].update({
                        "resolutionWidth": instance.data["resolutionWidth"],
                        "resolutionHeight": instance.data["resolutionHeight"],
                        "pixelAspect": instance.data["pixelAspect"]
                    })

            in_info['tasks'] = instance.data['tasks']
            in_info["comments"] = instance.data.get("comments", [])

            parents = instance.data.get('parents', [])
            self.log.debug("__ in_info: {}".format(in_info))

            actual = {name: in_info}

            for parent in reversed(parents):
                next_dict = {}
                parent_name = parent["entity_name"]
                next_dict[parent_name] = {}
                next_dict[parent_name]["entity_type"] = parent["entity_type"]
                next_dict[parent_name]["childs"] = actual
                actual = next_dict

            temp_context = self.update_dict(temp_context, actual)

        # TODO: 100% sure way of get project! Will be Name or Code?
        project_name = avalon.Session["AVALON_PROJECT"]
        final_context = {}
        final_context[project_name] = {}
        final_context[project_name]['entity_type'] = 'Project'
        final_context[project_name]['childs'] = temp_context

        # adding hierarchy context to instance
        context.data["hierarchyContext"] = final_context
        self.log.debug("context.data[hierarchyContext] is: {}".format(
            context.data["hierarchyContext"]))
