import os
import pyblish.api
import logging

if not os.environ.get("FTRACK_API_KEY"):
    import appdirs
    import json

    config_path = os.path.normpath(appdirs.user_data_dir('pype-app', 'pype'))
    action_file_name = 'ftrack_cred.json'
    action_fpath = os.path.join(config_path, action_file_name)

    validation = False
    credentials = {}
    try:
        file = open(action_fpath, 'r')
        credentials = json.load(file)
    except Exception:
        raise Exception("Ftrack credentials are missing ...")
    else:
        file.close()

    os.environ['FTRACK_API_USER'] = credentials["username"]
    os.environ['FTRACK_API_KEY'] = credentials["apiKey"]

try:
    import ftrack_api_old as ftrack_api
except Exception:
    import ftrack_api


class CollectFtrackApi(pyblish.api.ContextPlugin):
    """ Collects an ftrack session and the current task id. """

    order = pyblish.api.CollectorOrder
    label = "Collect Ftrack Api"

    def process(self, context):

        # Collect session
        session = ftrack_api.Session()
        context.data["ftrackSession"] = session

        # Collect task

        project = os.environ.get('AVALON_PROJECT', '')
        asset = os.environ.get('AVALON_ASSET', '')
        task = os.environ.get('AVALON_TASK', None)
        self.log.debug(task)

        if task:
            result = session.query('Task where\
                project.full_name is "{0}" and\
                name is "{1}" and\
                parent.name is "{2}"'.format(project, task, asset)).one()
            context.data["ftrackTask"] = result
        else:
            result = session.query('TypedContext where\
                project.full_name is "{0}" and\
                name is "{1}"'.format(project, asset)).one()
            context.data["ftrackEntity"] = result

        self.log.info(result)
