import shutil
import pyblish.api
import pyblish_standalone
import os
from bait.paths import get_env_work_file


class RepairCelactionScenePath(pyblish.api.Action):
    label = "Repair"
    icon = "wrench"
    on = "failed"

    def process(self, context, plugin):

        # get version data
        version = context.data('version') if context.has_data('version') else 1

        task_id = context.data["ftrackData"]["Task"]["id"]
        expected_path = get_env_work_file(
            "celaction", task_id, "scn", version).replace('\\\\\\', '\\\\')

        src = context.data["currentFile"]

        if not os.path.exists(os.path.dirname(expected_path)):
            os.makedirs(os.path.dirname(expected_path))

        if os.path.exists(os.path.dirname(expected_path)):
            self.log.info("existing to \"%s\"" % expected_path)

        if os.path.exists(expected_path) and ('v001' in expected_path):
            os.remove(expected_path)

        shutil.copy2(src, expected_path)

        pyblish_standalone.kwargs['path'] = [expected_path]
        context.data["currentFile"] = expected_path

        self.log.info("Saved to \"%s\"" % expected_path)


class ValidateCelactionScenePath(pyblish.api.InstancePlugin):
    order = pyblish.api.ValidatorOrder
    families = ['scene']
    label = 'Scene Path'
    actions = [RepairCelactionScenePath]

    def process(self, instance):

        # getting current work file
        current_scene_path = pyblish_standalone.kwargs['path'][0]

        version = instance.context.data(
            'version') if instance.context.has_data('version') else 1

        task_id = instance.context.data["ftrackData"]["Task"]["id"]
        expected_scene_path = get_env_work_file(
            "celaction", task_id, "scn", version).replace('\\\\\\', '\\\\')

        msg = 'Scene path is not correct: Current: {}, Expected: {}'.format(
            current_scene_path, expected_scene_path)

        assert expected_scene_path == current_scene_path, msg
