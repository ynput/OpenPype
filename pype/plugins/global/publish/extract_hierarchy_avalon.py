import pyblish.api
from avalon import io


class ExtractHierarchyToAvalon(pyblish.api.ContextPlugin):
    """Create entities in Avalon based on collected data."""

    order = pyblish.api.ExtractorOrder - 0.01
    label = "Extract Hierarchy To Avalon"
    families = ["clip", "shot"]

    def process(self, context):
        # processing starts here
        if "hierarchyContext" not in context.data:
            self.log.info("skipping IntegrateHierarchyToAvalon")
            return

        if not io.Session:
            io.install()

        active_assets = []
        hierarchy_context = context.data["hierarchyContext"]
        hierarchy_assets = self._get_assets(hierarchy_context)

        # filter only the active publishing insatnces
        for instance in context:
            if instance.data.get("publish") is False:
                continue

            if not instance.data.get("asset"):
                continue

            active_assets.append(instance.data["asset"])

        # filter out only assets which are activated as isntances
        new_hierarchy_assets = {k: v for k, v in hierarchy_assets.items()
                                if k in active_assets}

        # modify the hierarchy context so there are only fitred assets
        self._set_assets(hierarchy_context, new_hierarchy_assets)

        input_data = context.data["hierarchyContext"] = hierarchy_context

        self.project = None
        self.import_to_avalon(input_data)

    def import_to_avalon(self, input_data, parent=None):
        for name in input_data:
            self.log.info("input_data[name]: {}".format(input_data[name]))
            entity_data = input_data[name]
            entity_type = entity_data["entity_type"]

            data = {}
            data["entityType"] = entity_type

            # Custom attributes.
            for k, val in entity_data.get("custom_attributes", {}).items():
                data[k] = val

            if entity_type.lower() != "project":
                data["inputs"] = entity_data.get("inputs", [])

                # Tasks.
                tasks = entity_data.get("tasks", [])
                if tasks is not None or len(tasks) > 0:
                    data["tasks"] = tasks
                parents = []
                visualParent = None
                # do not store project"s id as visualParent (silo asset)
                if self.project is not None:
                    if self.project["_id"] != parent["_id"]:
                        visualParent = parent["_id"]
                        parents.extend(
                            parent.get("data", {}).get("parents", [])
                        )
                        parents.append(parent["name"])
                data["visualParent"] = visualParent
                data["parents"] = parents

            update_data = True
            # Process project
            if entity_type.lower() == "project":
                entity = io.find_one({"type": "project"})
                # TODO: should be in validator?
                assert (entity is not None), "Did not find project in DB"

                # get data from already existing project
                cur_entity_data = entity.get("data") or {}
                cur_entity_data.update(data)
                data = cur_entity_data

                self.project = entity
            # Raise error if project or parent are not set
            elif self.project is None or parent is None:
                raise AssertionError(
                    "Collected items are not in right order!"
                )
            # Else process assset
            else:
                entity = io.find_one({"type": "asset", "name": name})
                if entity:
                    # Do not override data, only update
                    cur_entity_data = entity.get("data") or {}
                    new_tasks = data.pop("tasks", [])
                    if "tasks" in cur_entity_data and new_tasks:
                        for task_name in new_tasks:
                            if task_name not in cur_entity_data["tasks"]:
                                cur_entity_data["tasks"].append(task_name)
                    cur_entity_data.update(data)
                    data = cur_entity_data
                else:
                    # Skip updating data
                    update_data = False

                    archived_entities = io.find({
                        "type": "archived_asset",
                        "name": name
                    })
                    unarchive_entity = None
                    for archived_entity in archived_entities:
                        archived_parents = (
                            archived_entity
                            .get("data", {})
                            .get("parents")
                        )
                        if data["parents"] == archived_parents:
                            unarchive_entity = archived_entity
                            break

                    if unarchive_entity is None:
                        # Create entity if doesn"t exist
                        entity = self.create_avalon_asset(name, data)
                    else:
                        # Unarchive if entity was archived
                        entity = self.unarchive_entity(unarchive_entity, data)

            if update_data:
                # Update entity data with input data
                io.update_many(
                    {"_id": entity["_id"]},
                    {"$set": {"data": data}}
                )

            if "childs" in entity_data:
                self.import_to_avalon(entity_data["childs"], entity)

    def unarchive_entity(self, entity, data):
        # Unarchived asset should not use same data
        new_entity = {
            "_id": entity["_id"],
            "schema": "avalon-core:asset-3.0",
            "name": entity["name"],
            "parent": self.project["_id"],
            "type": "asset",
            "data": data
        }
        io.replace_one(
            {"_id": entity["_id"]},
            new_entity
        )
        return new_entity

    def create_avalon_asset(self, name, data):
        item = {
            "schema": "avalon-core:asset-3.0",
            "name": name,
            "parent": self.project["_id"],
            "type": "asset",
            "data": data
        }
        self.log.debug("Creating asset: {}".format(item))
        entity_id = io.insert_one(item).inserted_id

        return io.find_one({"_id": entity_id})

    def _get_assets(self, input_dict):
        """ Returns only asset dictionary.
            Usually the last part of deep dictionary which
            is not having any children
        """
        for key in input_dict.keys():
            # check if child key is available
            if input_dict[key].get("childs"):
                # loop deeper
                return self._get_assets(input_dict[key]["childs"])
            else:
                # give the dictionary with assets
                return input_dict

    def _set_assets(self, input_dict, new_assets=None):
        """ Modify the hierarchy context dictionary.
            It will replace the asset dictionary with only the filtred one.
        """
        for key in input_dict.keys():
            # check if child key is available
            if input_dict[key].get("childs"):
                # return if this is just for testing purpose and no
                # new_assets property is avalable
                if not new_assets:
                    return True

                # test for deeper inner children availabelity
                if self._set_assets(input_dict[key]["childs"]):
                    # if one level deeper is still children available
                    # then process farther
                    self._set_assets(input_dict[key]["childs"], new_assets)
                else:
                    # or just assign the filtred asset ditionary
                    input_dict[key]["childs"] = new_assets
            else:
                # test didnt find more childs in input dictionary
                return None
