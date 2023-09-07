import collections

import pyblish.api
from ayon_api import create_link, make_sure_link_type_exists

from openpype import AYON_SERVER_ENABLED


class IntegrateInputLinksAYON(pyblish.api.ContextPlugin):
    """Connecting version level dependency links"""

    order = pyblish.api.IntegratorOrder + 0.2
    label = "Connect Dependency InputLinks AYON"

    def process(self, context):
        """Connect dependency links for all instances, globally

        Code steps:
        - filter instances that integrated version
            - have "versionEntity" entry in data
        - separate workfile instance within filtered instances
        - when workfile instance is available:
            - link all `loadedVersions` as input of the workfile
            - link workfile as input of all other integrated versions
        - link version's inputs if it's instance have "inputVersions" entry
        -

        inputVersions:
            The "inputVersions" in instance.data should be a list of
            version ids (str), which are the dependencies of the publishing
            instance that should be extracted from working scene by the DCC
            specific publish plugin.
        """

        workfile_instance, other_instances = self.split_instances(context)

        # Variable where links are stored in submethods
        new_links_by_type = collections.defaultdict(list)

        self.create_workfile_links(
            workfile_instance, other_instances, new_links_by_type)

        self.create_generative_links(other_instances, new_links_by_type)

        self.create_links_on_server(context, new_links_by_type)

    def split_instances(self, context):
        workfile_instance = None
        other_instances = []

        for instance in context:
            # Skip inactive instances
            if not instance.data.get("publish", True):
                continue

            version_doc = instance.data.get("versionEntity")
            if not version_doc:
                self.log.debug(
                    "Instance {} doesn't have version.".format(instance))
                continue

            family = instance.data.get("family")
            if family == "workfile":
                workfile_instance = instance
            else:
                other_instances.append(instance)
        return workfile_instance, other_instances

    def add_link(self, new_links_by_type, link_type, input_id, output_id):
        """Add dependency link data into temporary variable.

        Args:
            new_links_by_type (dict[str, list[dict[str, Any]]]): Object where
                output is stored.
            link_type (str): Type of link, one of 'reference' or 'generative'
            input_id (str): Input version id.
            output_id (str): Output version id.
        """

        new_links_by_type[link_type].append((input_id, output_id))

    def create_workfile_links(
        self, workfile_instance, other_instances, new_links_by_type
    ):
        if workfile_instance is None:
            self.log.warn("No workfile in this publish session.")
            return

        workfile_version_id = workfile_instance.data["versionEntity"]["_id"]
        # link workfile to all publishing versions
        for instance in other_instances:
            self.add_link(
                new_links_by_type,
                "generative",
                workfile_version_id,
                instance.data["versionEntity"]["_id"],
            )

        loaded_versions = workfile_instance.context.get("loadedVersions")
        if not loaded_versions:
            return

        # link all loaded versions in scene into workfile
        for version in loaded_versions:
            self.add_link(
                new_links_by_type,
                "reference",
                version["version"],
                workfile_version_id,
            )

    def create_generative_links(self, other_instances, new_links_by_type):
        for instance in other_instances:
            input_versions = instance.data.get("inputVersions")
            if not input_versions:
                continue

            version_entity = instance.data["versionEntity"]
            for input_version in input_versions:
                self.add_link(
                    new_links_by_type,
                    "generative",
                    input_version,
                    version_entity["_id"],
                )

    def create_links_on_server(self, context, new_links):
        """Create new links on server.

        Args:
            dict[str, list[tuple[str, str]]]: Version links by link type.
        """

        if not new_links:
            return

        project_name = context.data["projectName"]

        # Make sure link types are available on server
        for link_type in new_links.keys():
            make_sure_link_type_exists(
                project_name, link_type, "version", "version"
            )

        # Create link themselves
        for link_type, items in new_links.items():
            mapping = collections.defaultdict(set)
            # Make sure there are no duplicates of src > dst ids
            for item in items:
                _input_id, _output_id = item
                mapping[_input_id].add(_output_id)

            for input_id, output_ids in mapping.items():
                for output_id in output_ids:
                    create_link(
                        project_name,
                        link_type,
                        input_id,
                        "version",
                        output_id,
                        "version"
                    )


if not AYON_SERVER_ENABLED:
    del IntegrateInputLinksAYON
