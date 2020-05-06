import pyblish.api
from avalon import api


class CollectHierarchyContext(pyblish.api.ContextPlugin):
    """Collecting hierarchy context from `parents` and `hierarchy` data
    present in `clip` family instances coming from the request json data file

    It will add `hierarchical_context` into each instance for integrate
    plugins to be able to create needed parents for the context if they
    don't exist yet
    """

    label = "Collect Hierarchy Context"
    order = pyblish.api.CollectorOrder + 0.1

    def update_dict(self, ex_dict, new_dict):
        for key in ex_dict:
            if key in new_dict and isinstance(ex_dict[key], dict):
                new_dict[key] = self.update_dict(ex_dict[key], new_dict[key])
            else:
                new_dict[key] = ex_dict[key]
        return new_dict

    def process(self, context):
        json_data = context.data.get("jsonData", None)
        temp_context = {}
        for instance in json_data['instances']:
            if instance['family'] in 'workfile':
                continue

            in_info = {}
            name = instance['name']
            # suppose that all instances are Shots
            in_info['entity_type'] = 'Shot'

            instance_pyblish = [
                i for i in context.data["instances"]
                if i.data['asset'] in name][0]
            in_info['custom_attributes'] = {
                'frameStart': instance_pyblish.data['frameStart'],
                'frameEnd': instance_pyblish.data['frameEnd'],
                'handleStart': instance_pyblish.data['handleStart'],
                'handleEnd': instance_pyblish.data['handleEnd'],
                'fps': instance_pyblish.data['fps']
            }

            in_info['tasks'] = instance['tasks']

            parents = instance.get('parents', [])

            actual = {name: in_info}

            for parent in reversed(parents):
                next_dict = {}
                parent_name = parent["entityName"]
                next_dict[parent_name] = {}
                next_dict[parent_name]["entity_type"] = parent["entityType"]
                next_dict[parent_name]["childs"] = actual
                actual = next_dict

            temp_context = self.update_dict(temp_context, actual)
            self.log.debug(temp_context)

        # TODO: 100% sure way of get project! Will be Name or Code?
        project_name = api.Session["AVALON_PROJECT"]
        final_context = {}
        final_context[project_name] = {}
        final_context[project_name]['entity_type'] = 'Project'
        final_context[project_name]['childs'] = temp_context

        # adding hierarchy context to instance
        context.data["hierarchyContext"] = final_context
        self.log.debug("context.data[hierarchyContext] is: {}".format(
            context.data["hierarchyContext"]))
