import os
import acre

from avalon import api, lib, io
import pype.api as pype


class PremierePro(api.Action):

    name = "premiere_2019"
    label = "Premiere Pro"
    icon = "premiere_icon"
    order = 996

    def is_compatible(self, session):
        """Return whether the action is compatible with the session"""
        if "AVALON_TASK" in session:
            return True
        return False

    def process(self, session, **kwargs):
        """Implement the behavior for when the action is triggered

        Args:
            session (dict): environment dictionary

        Returns:
            Popen instance of newly spawned process

        """

        with pype.modified_environ(**session):
            # Get executable by name
            app = lib.get_application(self.name)
            executable = lib.which(app["executable"])

            # Run as server
            arguments = []

            tools_env = acre.get_tools([self.name])
            env = acre.compute(tools_env)
            env = acre.merge(env, current_env=dict(os.environ))

            if not env.get('AVALON_WORKDIR', None):
                project_name = env.get("AVALON_PROJECT")
                anatomy = pype.Anatomy(project_name)
                os.environ['AVALON_PROJECT'] = project_name
                io.Session['AVALON_PROJECT'] = project_name

                task_name = os.environ.get(
                    "AVALON_TASK", io.Session["AVALON_TASK"]
                )
                asset_name = os.environ.get(
                    "AVALON_ASSET", io.Session["AVALON_ASSET"]
                )
                application = lib.get_application(
                    os.environ["AVALON_APP_NAME"]
                )

                project_doc = io.find_one({"type": "project"})
                data = {
                    "task": task_name,
                    "asset": asset_name,
                    "project": {
                        "name": project_doc["name"],
                        "code": project_doc["data"].get("code", '')
                    },
                    "hierarchy": pype.get_hierarchy(),
                    "app": application["application_dir"]
                }
                anatomy_filled = anatomy.format(data)
                workdir = anatomy_filled["work"]["folder"]

                os.environ["AVALON_WORKDIR"] = workdir

            env.update(dict(os.environ))

            lib.launch(
                executable=executable,
                args=arguments,
                environment=env
            )
            return
