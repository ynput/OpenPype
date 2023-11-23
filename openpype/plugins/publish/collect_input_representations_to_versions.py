import pyblish.api

from bson.objectid import ObjectId

from openpype.client import get_representations


class CollectInputRepresentationsToVersions(pyblish.api.ContextPlugin):
    """Converts collected input representations to input versions.

    Any data in `instance.data["inputRepresentations"]` gets converted into
    `instance.data["inputVersions"]` as supported in OpenPype v3.

    """
    # This is a ContextPlugin because then we can query the database only once
    # for the conversion of representation ids to version ids (optimization)
    label = "Input Representations to Versions"
    order = pyblish.api.CollectorOrder + 0.499
    hosts = ["*"]

    def process(self, context):
        # Query all version ids for representation ids from the database once
        representations = set()
        for instance in context:
            inst_repre = instance.data.get("inputRepresentations", [])
            if inst_repre:
                representations.update(inst_repre)

        representations_docs = get_representations(
            project_name=context.data["projectEntity"]["name"],
            representation_ids=representations,
            fields=["_id", "parent"])

        representation_id_to_version_id = {
            str(repre["_id"]): repre["parent"]
            for repre in representations_docs
        }

        for instance in context:
            inst_repre = instance.data.get("inputRepresentations", [])
            if not inst_repre:
                continue

            input_versions = instance.data.setdefault("inputVersions", [])
            for repre_id in inst_repre:
                version_id = representation_id_to_version_id.get(repre_id)
                if version_id:
                    input_versions.append(version_id)
                else:
                    self.log.debug(
                        "Representation id {} skipped because its version is "
                        "not found in current project. Likely it is loaded "
                        "from a library project or uses a deleted "
                        "representation or version.".format(repre_id)
                    )
