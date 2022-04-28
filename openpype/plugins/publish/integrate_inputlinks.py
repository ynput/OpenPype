from collections import OrderedDict

from bson.objectid import ObjectId
import pyblish.api

from openpype.pipeline import legacy_io


class IntegrateInputLinks(pyblish.api.ContextPlugin):
    """Connecting version level dependency links"""

    order = pyblish.api.IntegratorOrder + 0.2
    label = "Connect Dependency InputLinks"

    def process(self, context):
        """Connect dependency links for all instances, globally

        Code steps:
        * filter out instances that has "versionEntity" entry in data
        * find workfile instance within context
        * if workfile found:
            - link all `loadedVersions` as input of the workfile
            - link workfile as input of all publishing instances
        * else:
            - show "no workfile" warning
        * link instances' inputs if it's data has "inputVersions" entry
        * Write into database

        inputVersions:
            The "inputVersions" in instance.data should be a list of
            version document's Id (str or ObjectId), which are the
            dependencies of the publishing instance that should be
            extracted from working scene by the DCC specific publish
            plugin.

        """
        workfile = None
        publishing = []

        for instance in context:
            if not instance.data.get("publish", True):
                # Skip inactive instances
                continue

            version_doc = instance.data.get("versionEntity")
            if not version_doc:
                self.log.debug("Instance %s doesn't have version." % instance)
                continue

            version_data = version_doc.get("data", {})
            families = version_data.get("families", [])

            if "workfile" in families:
                workfile = instance
            else:
                publishing.append(instance)

        if workfile is None:
            self.log.warn("No workfile in this publish session.")
        else:
            workfile_version_doc = workfile.data["versionEntity"]
            # link all loaded versions in scene into workfile
            for version in context.data.get("loadedVersions", []):
                self.add_link(
                    link_type="reference",
                    input_id=version["version"],
                    version_doc=workfile_version_doc,
                )
            # link workfile to all publishing versions
            for instance in publishing:
                self.add_link(
                    link_type="generative",
                    input_id=workfile_version_doc["_id"],
                    version_doc=instance.data["versionEntity"],
                )

        # link versions as dependencies to the instance
        for instance in publishing:
            for input_version in instance.data.get("inputVersions") or []:
                self.add_link(
                    link_type="generative",
                    input_id=input_version,
                    version_doc=instance.data["versionEntity"],
                )

        if workfile is not None:
            publishing.append(workfile)
        self.write_links_to_database(publishing)

    def add_link(self, link_type, input_id, version_doc):
        """Add dependency link data into version document

        Args:
            link_type (str): Type of link, one of 'reference' or 'generative'
            input_id (str or ObjectId): Document Id of input version
            version_doc (dict): The version document that takes the input

        Returns:
            None

        """
        # NOTE:
        # using OrderedDict() here is just for ensuring field order between
        # python versions, if we ever need to use mongodb operation '$addToSet'
        # to update and avoid duplicating elements in 'inputLinks' array in the
        # future.
        link = OrderedDict()
        link["type"] = link_type
        link["id"] = ObjectId(input_id)
        link["linkedBy"] = "publish"

        if "inputLinks" not in version_doc["data"]:
            version_doc["data"]["inputLinks"] = []
        version_doc["data"]["inputLinks"].append(link)

    def write_links_to_database(self, instances):
        """Iter instances in context to update database

        If `versionEntity.data.inputLinks` not None in `instance.data`, doc
        in database will be updated.

        """
        for instance in instances:
            version_doc = instance.data.get("versionEntity")
            if version_doc is None:
                continue

            input_links = version_doc["data"].get("inputLinks")
            if input_links is None:
                continue

            legacy_io.update_one(
                {"_id": version_doc["_id"]},
                {"$set": {"data.inputLinks": input_links}}
            )
