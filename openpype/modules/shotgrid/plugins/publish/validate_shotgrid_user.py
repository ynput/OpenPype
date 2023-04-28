import pyblish.api
from openpype.pipeline.publish import ValidateContentsOrder


class ValidateShotgridUser(pyblish.api.ContextPlugin):
    """
    Check if user is valid and have access to the project.
    """

    label = "Validate Shotgrid User"
    order = ValidateContentsOrder

    def process(self, context):
        sg = context.data.get("shotgridSession")

        login = context.data.get("shotgridUser")
        self.log.info("Login shotgrid set in OpenPype is {}".format(login))
        project = context.data.get("shotgridProject")
        self.log.info("Current shotgun project is {}".format(project))

        if not (login and sg and project):
            raise KeyError()

        ### Starts Alkemy-X Override ###
        # user = sg.find_one("HumanUser", [["login", "is", login]], ["projects"])
        user = sg.find_one("HumanUser", [["login", "is", login]], ["projects", "permission_rule_set"])
        admin = user["permission_rule_set"]["name"] == "Admin"
        ### Ends Alkemy-X Override ###

        self.log.info(user)
        self.log.info(login)
        user_projects_id = [p["id"] for p in user.get("projects", [])]
        ### Starts Alkemy-X Override ###
        # if not project.get("id") in user_projects_id:
        if not project.get("id") in user_projects_id and not admin:
        ### Ends Alkemy-X Override ###
            raise PermissionError(
                "Login {} don't have access to the project {}".format(
                    login, project
                )
            )

        self.log.info(
            "Login {} have access to the project {}".format(login, project)
        )
