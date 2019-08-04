import os
import pyblish.api
from avalon import (
    io,
    api as avalon
)
from pype import api as pype
import json


class CollectContextDataFromAport(pyblish.api.ContextPlugin):
    """
    Collecting temp json data sent from a host context
    and path for returning json data back to hostself.

    Setting avalon session into correct context

    Args:
        context (obj): pyblish context session

    """

    label = "Collect Aport Context"
    order = pyblish.api.CollectorOrder - 0.49

    def process(self, context):

        # get json paths from data
        rqst_json_data_path = context.data['rqst_json_data_path']
        post_json_data_path = context.data['post_json_data_path']

        # get avalon session data and convert \ to /
        session = avalon.session
        fix_paths = {k: v.replace("\\", "/") for k, v in session.items()
                     if isinstance(v, str)}
        session.update(fix_paths)
        context.data["avalonSession"] = session

        # get stagin directory from recieved path to json
        context.data["stagingDir"] = \
            staging_dir = os.path.dirname(
            post_json_data_path).replace("\\", "/")

        if not os.path.exists(staging_dir):
            os.makedirs(staging_dir)

        # get data from json file recieved
        with open(rqst_json_data_path) as f:
            context.data['json_data'] = json_data = json.load(f)
        assert json_data, "No `data` in json file"

        # get and check host type
        host = json_data.get("host", None)
        host_version = json_data.get("hostVersion", None)
        assert host, "No `host` data in json file"
        assert host_version, "No `hostVersion` data in json file"
        context.data["host"] = session["AVALON_APP"] = host
        context.data["hostVersion"] = \
            session["AVALON_APP_VERSION"] = host_version

        # register pyblish for filtering of hosts in plugins
        pyblish.api.deregister_all_hosts()
        pyblish.api.register_host(host)

        # get path to studio templates
        templates_dir = os.getenv("PYPE_CONFIG", None)
        assert templates_dir, "Missing `PYPE_CONFIG` in os.environ"

        # get presets for host
        presets_dir = os.path.join(templates_dir, "presets", host)
        assert os.path.exists(presets_dir), "Required path `{}` doesn't exist".format(presets_dir)

        # load all available preset json files
        preset_data = dict()
        for file in os.listdir(presets_dir):
            name, ext = os.path.splitext(file)
            with open(os.path.join(presets_dir, file)) as prst:
                preset_data[name] = json.load(prst)

        context.data['presets'] = preset_data
        assert preset_data, "No `presets` data in json file"
        self.log.debug("preset_data: {}".format(preset_data))

        # get current file
        current_file = json_data.get("currentFile", None)
        assert current_file, "No `currentFile` data in json file"
        context.data["currentFile"] = current_file

        # get project data from avalon
        project_data = pype.get_project()["data"]
        assert project_data, "No `project_data` data in avalon db"
        context.data["projectData"] = project_data
        self.log.debug("project_data: {}".format(project_data))

        # get asset data from avalon and fix all paths
        asset_data = pype.get_asset()["data"]
        assert asset_data, "No `asset_data` data in avalon db"
        asset_data = {k: v.replace("\\", "/") for k, v in asset_data.items()
                      if isinstance(v, str)}
        context.data["assetData"] = asset_data

        self.log.debug("asset_data: {}".format(asset_data))
        self.log.info("rqst_json_data_path is: {}".format(rqst_json_data_path))
        self.log.info("post_json_data_path is: {}".format(post_json_data_path))

        # self.log.info("avalon.session is: {}".format(avalon.session))
