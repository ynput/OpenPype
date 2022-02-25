from pymongo import UpdateOne
from bson.objectid import ObjectId

from avalon.api import AvalonMongoDB

from openpype_modules.ftrack.lib import (
    CUST_ATTR_ID_KEY,
    query_custom_attributes,

    BaseEvent
)


class SyncLinksToAvalon(BaseEvent):
    """Synchronize inpug linkts to avalon documents."""
    # Run after sync to avalon event handler
    priority = 110

    def __init__(self, session):
        self.dbcon = AvalonMongoDB()

        super(SyncLinksToAvalon, self).__init__(session)

    def launch(self, session, event):
        # Try to commit and if any error happen then recreate session
        entities_info = event["data"]["entities"]
        dependency_changes = []
        removed_entities = set()
        for entity_info in entities_info:
            action = entity_info.get("action")
            entityType = entity_info.get("entityType")
            if action not in ("remove", "add"):
                continue

            if entityType == "task":
                removed_entities.add(entity_info["entityId"])
            elif entityType == "dependency":
                dependency_changes.append(entity_info)

        # Care only about dependency changes
        if not dependency_changes:
            return

        project_id = None
        for entity_info in dependency_changes:
            for parent_info in entity_info["parents"]:
                if parent_info["entityType"] == "show":
                    project_id = parent_info["entityId"]
            if project_id is not None:
                break

        changed_to_ids = set()
        for entity_info in dependency_changes:
            to_id_change = entity_info["changes"]["to_id"]
            if to_id_change["new"] is not None:
                changed_to_ids.add(to_id_change["new"])

            if to_id_change["old"] is not None:
                changed_to_ids.add(to_id_change["old"])

        self._update_in_links(session, changed_to_ids, project_id)

    def _update_in_links(self, session, ftrack_ids, project_id):
        if not ftrack_ids or project_id is None:
            return

        attr_def = session.query((
            "select id from CustomAttributeConfiguration where key is \"{}\""
        ).format(CUST_ATTR_ID_KEY)).first()
        if attr_def is None:
            return

        project_entity = session.query((
            "select full_name from Project where id is \"{}\""
        ).format(project_id)).first()
        if not project_entity:
            return

        project_name = project_entity["full_name"]
        mongo_id_by_ftrack_id = self._get_mongo_ids_by_ftrack_ids(
            session, attr_def["id"], ftrack_ids
        )

        filtered_ftrack_ids = tuple(mongo_id_by_ftrack_id.keys())
        context_links = session.query((
            "select from_id, to_id from TypedContextLink where to_id in ({})"
        ).format(self.join_query_keys(filtered_ftrack_ids))).all()

        mapping_by_to_id = {
            ftrack_id: set()
            for ftrack_id in filtered_ftrack_ids
        }
        all_from_ids = set()
        for context_link in context_links:
            to_id = context_link["to_id"]
            from_id = context_link["from_id"]
            if from_id == to_id:
                continue
            all_from_ids.add(from_id)
            mapping_by_to_id[to_id].add(from_id)

        mongo_id_by_ftrack_id.update(self._get_mongo_ids_by_ftrack_ids(
            session, attr_def["id"], all_from_ids
        ))
        self.log.info(mongo_id_by_ftrack_id)
        bulk_writes = []
        for to_id, from_ids in mapping_by_to_id.items():
            dst_mongo_id = mongo_id_by_ftrack_id[to_id]
            links = []
            for ftrack_id in from_ids:
                link_mongo_id = mongo_id_by_ftrack_id.get(ftrack_id)
                if link_mongo_id is None:
                    continue

                links.append({
                    "id": ObjectId(link_mongo_id),
                    "linkedBy": "ftrack",
                    "type": "breakdown"
                })

            bulk_writes.append(UpdateOne(
                {"_id": ObjectId(dst_mongo_id)},
                {"$set": {"data.inputLinks": links}}
            ))

        if bulk_writes:
            self.dbcon.database[project_name].bulk_write(bulk_writes)

    def _get_mongo_ids_by_ftrack_ids(self, session, attr_id, ftrack_ids):
        output = query_custom_attributes(
            session, [attr_id], ftrack_ids, True
        )
        mongo_id_by_ftrack_id = {}
        for item in output:
            mongo_id = item["value"]
            if not mongo_id:
                continue

            ftrack_id = item["entity_id"]

            mongo_id_by_ftrack_id[ftrack_id] = mongo_id
        return mongo_id_by_ftrack_id


def register(session):
    '''Register plugin. Called when used as an plugin.'''
    SyncLinksToAvalon(session).register()
