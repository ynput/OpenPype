import os
import re
import json
import bson
import bson.json_util
from pype.modules.rest_api import RestApi, abort, CallbackResult
from pype.modules.ftrack.lib.custom_db_connector import DbConnector


class AvalonRestApi(RestApi):
    dbcon = DbConnector(
        os.environ["AVALON_MONGO"],
        os.environ["AVALON_DB"]
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dbcon.install()

    @RestApi.route("/projects/<project_name>", url_prefix="/avalon", methods="GET")
    def get_project(self, request):
        project_name = request.url_data["project_name"]
        if not project_name:
            output = {}
            for project_name in self.dbcon.tables():
                project = self.dbcon[project_name].find_one({
                    "type": "project"
                })
                output[project_name] = project

            return CallbackResult(data=self.result_to_json(output))

        project = self.dbcon[project_name].find_one({"type": "project"})

        if project:
            return CallbackResult(data=self.result_to_json(project))

        abort(404, "Project \"{}\" was not found in database".format(
            project_name
        ))

    @RestApi.route("/projects/<project_name>/assets/<asset>", url_prefix="/avalon", methods="GET")
    def get_assets(self, request):
        _project_name = request.url_data["project_name"]
        _asset = request.url_data["asset"]

        if not self.dbcon.exist_table(_project_name):
            abort(404, "Project \"{}\" was not found in database".format(
                _project_name
            ))

        if not _asset:
            assets = self.dbcon[_project_name].find({"type": "asset"})
            output = self.result_to_json(assets)
            return CallbackResult(data=output)

        # identificator can be specified with url query (default is `name`)
        identificator = request.query.get("identificator", "name")

        asset = self.dbcon[_project_name].find_one({
            "type": "asset",
            identificator: _asset
        })
        if asset:
            id = asset["_id"]
            asset["_id"] = str(id)
            return asset

        abort(404, "Asset \"{}\" with {} was not found in project {}".format(
            _asset, identificator, _project_name
        ))

    def result_to_json(self, result):
        """ Converts result of MongoDB query to dict without $oid (ObjectId)
        keys with help of regex matching.

        ..note:
            This will convert object type entries similar to ObjectId.
        """
        bson_json = bson.json_util.dumps(result)
        # Replace "{$oid: "{entity id}"}" with "{entity id}"
        regex1 = '(?P<id>{\"\$oid\": \"[^\"]+\"})'
        regex2 = '{\"\$oid\": (?P<id>\"[^\"]+\")}'
        for value in re.findall(regex1, bson_json):
            for substr in re.findall(regex2, value):
                bson_json = bson_json.replace(value, substr)

        return json.loads(bson_json)
