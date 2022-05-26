import pyblish.api

from openpype.pipeline import legacy_io


class CollectHierarchy(pyblish.api.ContextPlugin):
    """Collecting hierarchy from `parents`.

    present in `clip` family instances coming from the request json data file

    It will add `hierarchical_context` into each instance for integrate
    plugins to be able to create needed parents for the context if they
    don't exist yet
    """

    label = "Collect Hierarchy"
    order = pyblish.api.CollectorOrder - 0.076
    families = ["shot"]
    hosts = ["resolve", "hiero", "flame"]

    def process(self, context):
        temp_context = {}
        project_name = legacy_io.Session["AVALON_PROJECT"]
        final_context = {}
        final_context[project_name] = {}
        final_context[project_name]['entity_type'] = 'Project'

        for instance in context:
            self.log.info("Processing instance: `{}` ...".format(instance))

            # shot data dict
            shot_data = {}
            family = instance.data["family"]
            families = instance.data["families"]

            # filter out all unepropriate instances
            if not instance.data["publish"]:
                continue

            # exclude other families then self.families with intersection
            if not set(self.families).intersection(set(families + [family])):
                continue

            # exclude if not masterLayer True
            if not instance.data.get("heroTrack"):
                continue

            # get asset build data if any available
            shot_data["inputs"] = [
                x["_id"] for x in instance.data.get("assetbuilds", [])
            ]

            # suppose that all instances are Shots
            shot_data['entity_type'] = 'Shot'
            shot_data['tasks'] = instance.data.get("tasks") or {}
            shot_data["comments"] = instance.data.get("comments", [])

            shot_data['custom_attributes'] = {
                "handleStart": instance.data["handleStart"],
                "handleEnd": instance.data["handleEnd"],
                "frameStart": instance.data["frameStart"],
                "frameEnd": instance.data["frameEnd"],
                "clipIn": instance.data["clipIn"],
                "clipOut": instance.data["clipOut"],
                "fps": instance.data["fps"],
                "resolutionWidth": instance.data["resolutionWidth"],
                "resolutionHeight": instance.data["resolutionHeight"],
                "pixelAspect": instance.data["pixelAspect"]
            }

            actual = {instance.data["asset"]: shot_data}

            for parent in reversed(instance.data["parents"]):
                next_dict = {}
                parent_name = parent["entity_name"]
                next_dict[parent_name] = {}
                next_dict[parent_name]["entity_type"] = parent[
                    "entity_type"].capitalize()
                next_dict[parent_name]["childs"] = actual
                actual = next_dict

            temp_context = self._update_dict(temp_context, actual)

        # skip if nothing for hierarchy available
        if not temp_context:
            return

        final_context[project_name]['childs'] = temp_context

        # adding hierarchy context to context
        context.data["hierarchyContext"] = final_context
        self.log.debug("context.data[hierarchyContext] is: {}".format(
            context.data["hierarchyContext"]))

    def _update_dict(self, parent_dict, child_dict):
        """
        Nesting each children into its parent.

        Args:
            parent_dict (dict): parent dict wich should be nested with children
            child_dict (dict): children dict which should be injested
        """

        for key in parent_dict:
            if key in child_dict and isinstance(parent_dict[key], dict):
                child_dict[key] = self._update_dict(
                    parent_dict[key], child_dict[key]
                )
            else:
                if parent_dict.get(key) and child_dict.get(key):
                    continue
                else:
                    child_dict[key] = parent_dict[key]

        return child_dict
