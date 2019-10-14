import os
import re
import json
import bson
import bson.json_util
from pype.services.rest_api import RestApi, abort, CallbackResult, Query
from pype.ftrack.lib.custom_db_connector import DbConnector


class AvalonRestApi(RestApi):
    dbcon = DbConnector(
        os.environ["AVALON_MONGO"],
        os.environ["AVALON_DB"]
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dbcon.install()

    @RestApi.route("/projects/<project_name>", url_prefix="/avalon", methods="GET")
    def get_project(self, url_data):
        project_name = url_data["project_name"]
        if not project_name:
            output = {}
            for project_name in self.dbcon.tables():
                project = self.dbcon[project_name].find_one({"type": "project"})
                output[project_name] = project

            return CallbackResult(data=self.result_to_json(output))

        project = self.dbcon[project_name].find_one({"type": "project"})

        if project:
            return CallbackResult(data=self.result_to_json(project))

        abort(404, "Project \"{}\" was not found in database".format(
            project_name
        ))

    @RestApi.route("/projects/<project_name>/assets/<asset>", url_prefix="/avalon", methods="GET")
    def get_assets(self, url_data, query:Query):
        _project_name = url_data["project_name"]
        _asset = url_data["asset"]

        if not self.dbcon.exist_table(_project_name):
            abort(404, "Project \"{}\" was not found in database".format(
                project_name
            ))

        if not _asset:
            assets = self.dbcon[_project_name].find({"type": "asset"})
            output = self.result_to_json(assets)
            return CallbackResult(data=output)

        identificator = query.get("identificator", "name")

        asset = self.dbcon[_project_name].find_one({
            "type": "asset",
            identificator: _asset
        })
        if asset:
            id = asset["_id"]
            asset["_id"] = str(id)
            return asset

        abort(404, "Asset \"{}\" with {} was not found in project {}".format(
            _asset, identificator, project_name
        ))

    def result_to_json(self, result):
        bson_json = bson.json_util.dumps(result)
        # Replace "{$oid: "{entity id}"}" with "{entity id}"
        regex1 = '(?P<id>{\"\$oid\": \"[^\"]+\"})'
        regex2 = '{\"\$oid\": (?P<id>\"[^\"]+\")}'
        for value in re.findall(regex1, bson_json):
            for substr in re.findall(regex2, value):
                bson_json = bson_json.replace(value, substr)

        return json.loads(bson_json)
