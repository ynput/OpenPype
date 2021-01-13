import os
import sys
import json
import tempfile
import datetime
import traceback
from pype.modules.ftrack import ServerAction
from avalon.api import AvalonMongoDB
import pype


class PackWorkfilesAction(ServerAction):
    ignore_me = False
    identifier = "pack.workfiles.server"
    label = "Pype Admin"
    variant = "- Pack workfiles"
    db_con = AvalonMongoDB()

    def discover(self, session, entities, event):
        """Defines if action will be discovered for a selection."""
        allowed = ["task"]
        if entities[0].entity_type.lower() not in allowed:
            return False
        return True

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
        try:
            self.pack_workfiles(session, entities, event)

        except Exception:
            self.handle_exception(job, session, sys.exc_info(), event)
            return

        job["status"] = "done"
        session.commit()

    def pack_workfiles(self, session, entities, event):
        project_entity = self.get_project_from_entity(entities[0])
        project_name = project_entity["full_name"]
        self.db_con.install()
        self.db_con.Session["AVALON_PROJECT"] = project_name
        project_doc = self.db_con.find_one({"type": "project"})

        if not project_doc:
            Exception((
                "Didn't found project \"{}\" in avalon."
            ).format(project_name))

        allowed_task_names = ["compositing"]
        for entity in entities:
            if entity['name'] not in allowed_task_names:
                self.log.warning(f"Not allowed task name: `{entity['name']}`!")
                continue
            self.db_con.Session["AVALON_ASSET"] = entity["parent"]["name"]
            self.db_con.Session["AVALON_TASK"] = entity['name']
            pype.lib.make_workload_package(self.db_con.Session)
        self.db_con.uninstall()

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


def register(session, plugins_presets={}):
    PackWorkfilesAction(session, plugins_presets).register()
