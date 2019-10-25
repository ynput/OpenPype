"""
Requires:
    session     -> AVALON_PROJECT
    context     -> anatomy (pypeapp.Anatomy)
    instance    -> subset
    instance    -> asset
    instance    -> family

Provides:
    instance    -> template
    instance    -> assumedTemplateData
    instance    -> assumedDestination
"""

import os

from avalon import io, api
import pyblish.api


class CollectTemplates(pyblish.api.InstancePlugin):
    """Fill templates with data needed for publish"""

    order = pyblish.api.CollectorOrder + 0.1
    label = "Collect and fill Templates"
    hosts = ["maya", "nuke", "standalonepublisher"]

    def process(self, instance):
        # get all the stuff from the database
        subset_name = instance.data["subset"]
        asset_name = instance.data["asset"]
        project_name = api.Session["AVALON_PROJECT"]

        project = io.find_one({"type": "project",
                               "name": project_name},
                              projection={"config": True, "data": True})

        template = project["config"]["template"]["publish"]
        anatomy = instance.context.data['anatomy']

        asset = io.find_one({"type": "asset",
                             "name": asset_name,
                             "parent": project["_id"]})

        assert asset, ("No asset found by the name '{}' "
                       "in project '{}'".format(asset_name, project_name))
        silo = asset.get('silo')

        subset = io.find_one({"type": "subset",
                              "name": subset_name,
                              "parent": asset["_id"]})

        # assume there is no version yet, we start at `1`
        version = None
        version_number = 1
        if subset is not None:
            version = io.find_one({"type": "version",
                                   "parent": subset["_id"]},
                                  sort=[("name", -1)])

        # if there is a subset there ought to be version
        if version is not None:
            version_number += int(version["name"])

        hierarchy = asset['data']['parents']
        if hierarchy:
            # hierarchy = os.path.sep.join(hierarchy)
            hierarchy = os.path.join(*hierarchy)

        template_data = {"root": api.Session["AVALON_PROJECTS"],
                         "project": {"name": project_name,
                                     "code": project['data']['code']},
                         "silo": silo,
                         "family": instance.data['family'],
                         "asset": asset_name,
                         "subset": subset_name,
                         "version": version_number,
                         "hierarchy": hierarchy,
                         "representation": "TEMP"}

        instance.data["template"] = template
        instance.data["assumedTemplateData"] = template_data

        # We take the parent folder of representation 'filepath'
        instance.data["assumedDestination"] = os.path.dirname(
            (anatomy.format(template_data))["publish"]["path"]
        )
