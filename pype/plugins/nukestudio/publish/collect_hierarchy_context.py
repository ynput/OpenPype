import pyblish.api
from avalon import api


class CollectHierarchyContext(pyblish.api.InstancePlugin):
    """Collecting hierarchy context from `parents` and `hierarchy` data
    present in `clip` family instances coming from the request json data file

    It will add `hierarchical_context` into each instance for integrate
    plugins to be able to create needed parents for the context if they
    don't exist yet
    """

    label = "Collect Hierarchy Context"
    order = pyblish.api.CollectorOrder + 0.1
    families = ["clip"]

    def update_dict(self, ex_dict, new_dict):
        for key in ex_dict:
            if key in new_dict and isinstance(ex_dict[key], dict):
                new_dict[key] = self.update_dict(ex_dict[key], new_dict[key])
            else:
                new_dict[key] = ex_dict[key]
        return new_dict

    def convert_to_entity(self, key, value):
        types = {"shot": "Shot",
                 "folder": "Folder",
                 "episode": "Episode",
                 "Sequence": "Sequence",
                 }
        return {"entity_type": types.get(key, None), "entity_name": value}

    def process(self, instance):
        context = instance.context
        tags = instance.data.get("tags", None)
        self.log.info(tags)
        if tags:
            for t in tags:
                t_metadata = dict(t["metadata"])
                t_type = t_metadata.get("tag._type", "")
                if "hierarchy" in t_type:
                    self.log.info("__ type: {}".format(t_type))
                    d_metadata = dict()
                    for k, v in t_metadata.items():
                        new_k = k.split(".")[1]
                        try:
                            d_metadata[new_k] = str(v).format(**context.data)
                        except Exception:
                            d_metadata[new_k] = v


                    self.log.info("__ projectroot: {}".format(context.data["projectroot"]))
                    self.log.info("__ d_metadata: {}".format(d_metadata))
                    self.log.info(
                        "__ hierarchy: {}".format(d_metadata["note"]))
                    # self.log.info("__ hierarchy.format: {}".format(d_metadata["note"].format(
                    #     **d_metadata)))

        #
        # json_data = context.data.get("jsonData", None)
        # temp_context = {}
        # for instance in json_data['instances']:
        #     if instance['family'] in 'projectfile':
        #         continue
        #
        #     in_info = {}
        #     name = instance['name']
        #     # suppose that all instances are Shots
        #     in_info['entity_type'] = 'Shot'
        #
        #     instance_pyblish = [
        #         i for i in context.data["instances"] if i.data['asset'] in name][0]
        #     in_info['custom_attributes'] = {
        #         'fend': instance_pyblish.data['endFrame'],
        #         'fstart': instance_pyblish.data['startFrame'],
        #         'fps': instance_pyblish.data['fps']
        #     }
        #
        #     in_info['tasks'] = instance['tasks']
        #
        #     parents = instance.get('parents', [])
        #
        #     actual = {name: in_info}
        #
        #     for parent in reversed(parents):
        #         next_dict = {}
        #         parent_name = parent["entityName"]
        #         next_dict[parent_name] = {}
        #         next_dict[parent_name]["entity_type"] = parent["entityType"]
        #         next_dict[parent_name]["childs"] = actual
        #         actual = next_dict
        #
        #     temp_context = self.update_dict(temp_context, actual)
        #     self.log.debug(temp_context)
        #
        # # TODO: 100% sure way of get project! Will be Name or Code?
        # project_name = api.Session["AVALON_PROJECT"]
        # final_context = {}
        # final_context[project_name] = {}
        # final_context[project_name]['entity_type'] = 'Project'
        # final_context[project_name]['childs'] = temp_context
        #
        # # adding hierarchy context to instance
        # context.data["hierarchyContext"] = final_context
        # self.log.debug("context.data[hierarchyContext] is: {}".format(
        #     context.data["hierarchyContext"]))
