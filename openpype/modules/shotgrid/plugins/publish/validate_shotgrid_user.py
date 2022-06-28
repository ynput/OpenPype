import pyblish.api
import openpype.api


class ValidateShotgridUser(pyblish.api.ContextPlugin):
    """
    Check if user is valid and have access to the project.
    """

    label = "Validate Shotgrid User"
    order = openpype.api.ValidateContentsOrder

    def process(self, context):
        sg = context.data.get("shotgridSession")

        login = context.data.get("shotgridUser")
        self.log.info("Login shotgrid set in OpenPype is {}".format(login))
        project = context.data.get("shotgridProject")
        self.log.info("Current shotgun project is {}".format(project))

        if not (login and sg and project):
            raise KeyError()

        user = sg.find_one("HumanUser", [["login", "is", login]], ["projects"])

        self.log.info(user)
        self.log.info(login)
        user_projects_id = [p["id"] for p in user.get("projects", [])]
        if not project.get("id") in user_projects_id:
            raise PermissionError(
                "Login {} don't have access to the project {}".format(
                    login, project
                )
            )

        self.log.info(
            "Login {} have access to the project {}".format(login, project)
        )
