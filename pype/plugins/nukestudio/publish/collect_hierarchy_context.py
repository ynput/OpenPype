import pyblish.api
from avalon import api
import re


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

    def process(self, instance):
        context = instance.context
        tags = instance.data.get("tags", None)
        clip = instance.data["item"]
        asset = instance.data.get("asset")

        # build data for inner nukestudio project property
        data = {
            "sequence": context.data['activeSequence'].name().replace(' ', '_'),
            "track": clip.parent().name().replace(' ', '_'),
            "clip": asset
        }
        self.log.info("__ data: {}".format(data))

        # checking if tags are available
        if not tags:
            return

        # loop trough all tags
        for t in tags:
            t_metadata = dict(t["metadata"])
            t_type = t_metadata.get("tag.label", "")
            t_note = t_metadata.get("tag.note", "")

            # and finding only hierarchical tag
            if "hierarchy" in t_type.lower():
                d_metadata = dict()
                parents = list()

                # take template from Tag.note and break it into parts
                patern = re.compile(r"^\{([a-z]*?)\}")
                par_split = [patern.findall(t)[0]
                             for t in t_note.split("/")]

                # format all {} in two layers
                for k, v in t_metadata.items():
                    new_k = k.split(".")[1]
                    try:
                        # first try all data and context data to
                        # add to individual properties
                        new_v = str(v).format(
                            **dict(context.data, **data))
                        d_metadata[new_k] = new_v

                        # create parents
                        # find matching index of order
                        p_match_i = [i for i, p in enumerate(par_split)
                                     if new_k in p]

                        # if any is matching then convert to entity_types
                        if p_match_i:
                            self.log.info("__ new_k: {}".format(new_k))
                            self.log.info("__ new_v: {}".format(new_v))
                            parent = self.convert_to_entity(new_k, new_v)
                            parents.insert(p_match_i[0], parent)
                    except Exception:
                        d_metadata[new_k] = v

                # lastly fill those individual properties itno
                # main template from Tag.note
                hierarchy = d_metadata["note"].format(
                    **d_metadata)

                # check if hierarchy attribute is already created
                # it should not be so return warning if it is
                hd = instance.data.get("hierarchy")
                self.log.info("__ hd: {}".format(hd))
                assert not hd, "Only one Hierarchy Tag is \
                            allowed. Clip: `{}`".format(asset)

                # add formated hierarchy path into instance data
                instance.data["hierarchy"] = hierarchy
                instance.data["parents"] = parents
                self.log.info("__ hierarchy.format: {}".format(hierarchy))
                self.log.info("__ parents: {}".format(parents))
                self.log.info("__ d_metadata: {}".format(d_metadata))

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
