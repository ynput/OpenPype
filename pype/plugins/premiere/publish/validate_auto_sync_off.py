import pyblish.api
import pype.api
import avalon.api


class ValidateAutoSyncOff(pyblish.api.ContextPlugin):
    """Ensure that autosync value in ftrack project is set to False.

    In case was set to True and event server with the sync to avalon event
    is running will cause integration to avalon will be override.

    """

    order = pyblish.api.ValidatorOrder
    families = ['clip']
    label = 'Ftrack project\'s auto sync off'
    actions = [pype.api.RepairAction]

    def process(self, context):
        session = context.data["ftrackSession"]
        project_name = avalon.api.Session["AVALON_PROJECT"]
        query = 'Project where full_name is "{}"'.format(project_name)
        project = session.query(query).one()
        invalid = self.get_invalid(context)

        assert not invalid, (
            "Ftrack Project has 'Auto sync' set to On."
            " That may cause issues during integration."
        )

    @staticmethod
    def get_invalid(context):
        session = context.data["ftrackSession"]
        project_name = avalon.api.Session["AVALON_PROJECT"]
        query = 'Project where full_name is "{}"'.format(project_name)
        project = session.query(query).one()

        invalid = None

        if project.get('custom_attributes', {}).get(
                'avalon_auto_sync', False):
            invalid = project

        return invalid

    @classmethod
    def repair(cls, context):
        session = context.data["ftrackSession"]
        invalid = cls.get_invalid(context)
        invalid['custom_attributes']['avalon_auto_sync'] = False
        session.commit()
