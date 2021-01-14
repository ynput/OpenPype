import os
import sys
import json
import tempfile
import datetime
import collections
import traceback
from pype.modules.ftrack import ServerAction
from avalon.api import AvalonMongoDB
from pype.lib.packaging import make_workload_package_for_tasks


class PackWorkfilesAction(ServerAction):
    ignore_me = False
    identifier = "pack.workfiles.server"
    label = "Pype Admin"
    variant = "- Pack workfiles"

    allowed_task_names = ["compositing"]

    def __init__(self, *args, **kwargs):
        super(PackWorkfilesAction, self).__init__(*args, **kwargs)
        self.dbcon = AvalonMongoDB()

    def discover(self, session, entities, event):
        """Defines if action will be discovered for a selection."""
        for entity in entities:
            if entity.entity_type.lower() == "task":
                return True
        return False

    def launch(self, session, entities, event):
        """Workfile pack action trigger callback."""
        # Get user for job entity
        user_id = event["source"]["user"]["id"]
        user = session.query("User where id is \"{}\"".format(user_id)).one()

        # Create job
        job_data = {
            "description": "Preparing status changes report."
        }
        job = session.create("Job", {
            "user": user,
            "status": "running",
            "data": json.dumps(job_data)
        })
        session.commit()

        # Run action logic and handle errors
        self.dbcon.install()
        try:
            result = self.prepare_and_pack_workfiles(session, entities)

        except Exception as exc:
            self.handle_exception(job, session, sys.exc_info(), event)
            return {
                "success": False,
                "message": "Error: {}".format(str(exc))
            }

        finally:
            self.dbcon.uninstall()

        job["status"] = "done"
        session.commit()

        if result is not None:
            return result
        return True

    def prepare_and_pack_workfiles(self, session, entities):
        """Prepares data for packaging of last workfiles.

        Filter selected entities and keep only `Task` entity types with names
        specified in `allowed_task_names`.

        Collect parent ftrack ids of filtered tasks which are used to query
        asset documents.

        If asset documents are not found by `data.ftrackId` then fallback to
        find documents by names is executed. Entities that are not found even
        with fallback are skipped.

        Then selection of task entities is pointed to asset document and lib
        function `make_workload_package_for_tasks` is executed.

        Args:
            session (ftrack_api.Session): Ftrack session to be able query
                entities.
            entities (list): List of selected entities on which action was
                triggered.

        Returns:
            None: If everything if Ok.
            dict: Result of action with message.

        Raises:
            Exception: Method may raise any exception mainly due to
                `make_workload_package_for_tasks` function from lib.
        """
        project_entity = self.get_project_from_entity(entities[0])
        project_name = project_entity["full_name"]

        self.dbcon.Session["AVALON_PROJECT"] = project_name
        project_doc = self.dbcon.find_one({"type": "project"})
        if not project_doc:
            return {
                "success": False,
                "message": "Project \"{}\" was not found in avalon.".format(
                    project_name
                )
            }

        # Collect task entities and theird parent ids
        task_entities_by_parent_id = collections.defaultdict(list)
        for entity in entities:
            if entity.entity_type.lower() != "task":
                continue

            if entity["name"] not in self.allowed_task_names:
                self.log.warning(f"Not allowed task name: `{entity['name']}`!")
                continue

            parent_id = entity["parent_id"]
            task_entities_by_parent_id[parent_id].append(entity)

        parent_ftrack_ids = set(task_entities_by_parent_id.keys())

        # Query asset documents by collected parent ids
        # NOTE variable `asset_docs` can be used only once
        asset_docs = self.dbcon.find({
            "type": "asset",
            "data.ftrackId": {"$in": list(parent_ftrack_ids)}
        })

        # This variable should be used in future lines
        asset_docs_by_id = {}
        selected_task_names_by_asset_id = {}
        found_parent_ids = set()
        for asset_doc in asset_docs:
            # Store asset by it's mongo id
            asset_id = asset_doc["_id"]
            asset_docs_by_id[asset_id] = asset_doc
            # Store found ftrack ids
            ftrack_id = asset_doc["data"]["ftrackId"]
            found_parent_ids.add(ftrack_id)

            # Store task names related to the parent
            selected_task_names_by_asset_id[asset_id] = []
            for task_entity in task_entities_by_parent_id[ftrack_id]:
                selected_task_names_by_asset_id[asset_id].append(
                    task_entity["name"]
                )

        # Handle not found entities
        not_found_parent_ids = parent_ftrack_ids - found_parent_ids
        if not_found_parent_ids:
            self.log.warning((
                "There are few asset documents that were"
                " not found by Ftrack id. {}".format(not_found_parent_ids)
            ))
            missing_docs_by_ftrack_id, missing_ftrack_ids = (
                self.find_asset_docs_by_name(session, not_found_parent_ids)
            )
            for ftrack_id, asset_doc in missing_docs_by_ftrack_id.items():
                asset_id = asset_doc["_id"]
                asset_docs_by_id[asset_id] = asset_doc
                for task_entity in task_entities_by_parent_id[ftrack_id]:
                    selected_task_names_by_asset_id[asset_id].append(
                        task_entity["name"]
                    )

            # Should we say to user that he need to synchronize?
            # - or tell him which tasks were not prepared?
            self.log.warning((
                "There are still some parents without asset document."
                " Ftrack ids: {}"
            ).format(self.join_query_keys(missing_ftrack_ids)))

        if not asset_docs_by_id:
            return {
                "success": False,
                "message": (
                    "Didn't found documents in pipeline database. Try to sync"
                    " the project first."
                )
            }

        make_workload_package_for_tasks(
            project_doc, asset_docs_by_id, selected_task_names_by_asset_id
        )

    def find_asset_docs_by_name(self, session, not_found_parent_ids):
        """Try to find missing asset documents by their name.

        That may happend when `data.ftrackId` is not filled due to bad
        synchronization. This is fallback. Best case scenario is to not get
        here.

        Args:
            session (ftrack_api.Session): Ftrack session to be able query.
            not_found_parent_ids (list): List of ftrack ids that didn't match
                any `data.ftrackId` in asset docs.

        Returns:
            tuple: Output contain 2 items. (1)Asset documents by ftrack id and
                (2) list of ftrack ids which didn't match any name.
        """
        parent_entities = session.query(
            "select id, name from TypedContext where id in ({})".format(
                self.join_query_keys(not_found_parent_ids)
            )
        ).all()
        parent_ids_by_name = {
            parent_entity["name"]: parent_entity["id"]
            for parent_entity in parent_entities
        }
        parent_names = set(parent_ids_by_name.keys())
        asset_docs = self.dbcon.find({
            "type": "asset",
            "name": {"$in": list(parent_names)}
        })

        asset_docs_by_ftrack_id = {}
        found_asset_names = set()
        for asset_doc in asset_docs:
            asset_name = asset_doc["name"]
            # Store found name
            found_asset_names.add(asset_name)
            # Store document by ftrack id to be able pair selected tasks
            ftrack_id = parent_ids_by_name[asset_name]
            asset_docs_by_ftrack_id[ftrack_id] = asset_doc

        # Get not found asset documents
        missing_names = parent_names - found_asset_names
        # Get ftrack ids of not found assets
        missing_parent_ids = [
            parent_ids_by_name[missing_name]
            for missing_name in missing_names
        ]
        return asset_docs_by_ftrack_id, missing_parent_ids

    def add_component_to_job(self, job, session, filepath, basename=None):
        """Add filepath as downloadable component to job.

        Args:
            job (JobEntity): Entity of job where file should be able to
                download.
            session (Session): Ftrack session which was used to query/create
                entered job.
            filepath (str): Path to file which should be added to job.
            basename (str): Defines name of file which will be downloaded on
                user's side. Must be without extension otherwise extension will
                be duplicated in downloaded name. Basename from entered path
                used when not entered.
        """
        # Make sure session's locations are configured
        session._configure_locations()
        # Query `ftrack.server` location where component will be stored
        location = session.query(
            "Location where name is \"ftrack.server\""
        ).one()

        # Use filename as basename if not entered (must be without extension)
        if basename is None:
            basename = os.path.splitext(
                os.path.basename(filepath)
            )[0]

        component = session.create_component(
            filepath,
            data={"name": basename},
            location=location
        )
        session.create(
            "JobComponent",
            {
                "component_id": component["id"],
                "job_id": job["id"]
            }
        )
        session.commit()

    def handle_exception(self, job, session, exc_info, event):
        """Handle unexpected crash of action processing."""
        job_data = {
            "description": (
                "Workfiles preparation crashed! (Click to download traceback)"
            )
        }
        job["data"] = json.dumps(job_data)
        job["status"] = "failed"

        # Create temp file where traceback will be stored
        temp_obj = tempfile.NamedTemporaryFile(
            mode="w", prefix="pype_ftrack_", suffix=".txt", delete=False
        )
        temp_obj.close()
        temp_filepath = temp_obj.name

        # Store traceback to file
        result = traceback.format_exception(*exc_info)
        with open(temp_filepath, "w") as temp_file:
            temp_file.write("".join(result))

        # Upload file with traceback to ftrack server and add it to job
        component_basename = "{}_{}".format(
            self.__class__.__name__,
            datetime.datetime.now().strftime("%y-%m-%d-%H%M")
        )
        self.add_component_to_job(
            job, session, temp_filepath, component_basename
        )
        # Delete temp file
        os.remove(temp_filepath)

        msg = "Failed to prepare notes."
        self.log.warning(msg, exc_info=True)
        self.show_message(event, msg, False)


def register(session, plugins_presets=None):
    plugins_presets = plugins_presets or {}
    PackWorkfilesAction(session, plugins_presets).register()
