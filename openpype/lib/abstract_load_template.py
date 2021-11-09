import os
import re
import avalon
from openpype.settings import get_project_settings
from openpype.lib import Anatomy
from openpype.lib import get_linked_assets

# Copy from BuildWorkfile in avalon_context.py
# TODO : Move those function into a lib


def _collect_last_version_repres(asset_entities):
    """Collect subsets, versions and representations for asset_entities.

    Args:
        asset_entities (list): Asset entities for which want to find data

    Returns:
        (dict): collected entities

    Example output:
    ```
    {
        {Asset ID}: {
            "asset_entity": <AssetEntity>,
            "subsets": {
                {Subset ID}: {
                    "subset_entity": <SubsetEntity>,
                    "version": {
                        "version_entity": <VersionEntity>,
                        "repres": [
                            <RepreEntity1>, <RepreEntity2>, ...
                        ]
                    }
                },
                ...
            }
        },
        ...
    }
    output[asset_id]["subsets"][subset_id]["version"]["repres"]
    ```
    """

    if not asset_entities:
        return {}

    asset_entity_by_ids = {asset["_id"]: asset for asset in asset_entities}

    subsets = list(avalon.io.find({
        "type": "subset",
        "parent": {"$in": asset_entity_by_ids.keys()}
    }))
    subset_entity_by_ids = {subset["_id"]: subset for subset in subsets}

    sorted_versions = list(avalon.io.find({
        "type": "version",
        "parent": {"$in": subset_entity_by_ids.keys()}
    }).sort("name", -1))

    subset_id_with_latest_version = []
    last_versions_by_id = {}
    for version in sorted_versions:
        subset_id = version["parent"]
        if subset_id in subset_id_with_latest_version:
            continue
        subset_id_with_latest_version.append(subset_id)
        last_versions_by_id[version["_id"]] = version

    repres = avalon.io.find({
        "type": "representation",
        "parent": {"$in": last_versions_by_id.keys()}
    })

    output = {}
    for repre in repres:
        version_id = repre["parent"]
        version = last_versions_by_id[version_id]

        subset_id = version["parent"]
        subset = subset_entity_by_ids[subset_id]

        asset_id = subset["parent"]
        asset = asset_entity_by_ids[asset_id]

        if asset_id not in output:
            output[asset_id] = {
                "asset_entity": asset,
                "subsets": {}
            }

        if subset_id not in output[asset_id]["subsets"]:
            output[asset_id]["subsets"][subset_id] = {
                "subset_entity": subset,
                "version": {
                    "version_entity": version,
                    "repres": []
                }
            }

        output[asset_id]["subsets"][subset_id]["version"]["repres"].append(
            repre
        )

    return output


def get_loader_by_name():

    loaders_by_name = {}
    for loader in avalon.api.discover(avalon.api.Loader):
        loader_name = loader.__name__
        if loader_name in loaders_by_name:
            raise KeyError(
                "Duplicated loader name {0}!".format(loader_name)
            )
        loaders_by_name[loader_name] = loader
    return loaders_by_name


class AbstractTemplateLoader(object):
    """
    Property returning template path. Avoiding getter.
    Getting template path from open pype settings
    bassing on current avalon session
    and solving the path variables if needed.

    Properties:
        template_path (str) :

    Methods:
        get_representations
        get_valid_representations_id_for_placeholder
        validate_representation
        _get_node_data
        import_template
        switch
        get_template_nodes
    """

    @property
    def template_path(self):
        """
        Property returning template path. Avoiding getter.
        Getting template path from open pype settings
        bassing on current avalon session
        and solving the path variables if needed.

        Returns:
            str: Solved template path

        Raises:
            ValueError: No profile found from settings for current avalon
                session
            KeyError: Could not solve path because a key does not exists
                in avalon context
            IOError: Solved path does not exists on current filesystem
        """
        project = avalon.io.Session["AVALON_PROJECT"]
        anatomy = Anatomy(project)
        project_settings = get_project_settings(project)
        current_dcc = avalon.io.Session["AVALON_APP"]
        current_task = avalon.io.Session["AVALON_TASK"]
        profiles = project_settings[current_dcc]['workfile_build']['profiles']

        for profile in profiles:
            if current_task in profile['task_types']:
                path = profile['path']
                break
        else:
            raise ValueError(
                "No matching profile found for task '{}' in DCC '{}'".format(
                    current_task, current_dcc)
            )

        try:
            # while solved_path != new_solved_path
            solved_path = os.path.normpath(anatomy.path_remapper(path))
        except KeyError as missing_key:
            raise KeyError(
                "Could not solve key '{}' in template path '{}'".format(
                    missing_key, path))

        if not os.path.exists(solved_path):
            raise IOError(
                "Template found in openPype settings for task '{}' with DCC \
                '{}' does not exists. (Not found : {})".format(
                    current_task, current_dcc, solved_path))
        return solved_path

    def __init__(self, placeholder_class):

        self.import_template(self.template_path)

        loaders_by_name = get_loader_by_name()

        # Skip if there is no loader
        if not loaders_by_name:
            self.log.warning("There are no registered loaders.")
            return

        current_asset = avalon.io.Session["AVALON_ASSET"]
        current_asset_entity = avalon.io.find_one({
            "type": "asset",
            "name": current_asset
        })

        linked_asset_entities = get_linked_assets(current_asset_entity)
        version_repres = _collect_last_version_repres([current_asset_entity] + linked_asset_entities)

        linked_representations_by_id = {representation['_id'] : representation
            for asset in version_repres.values()
            for subset in asset['subsets'].values()
            for representation in subset['version']['repres']}
        context_representations_by_id = dict()

        for k in linked_representations_by_id.keys():
            if linked_representations_by_id[k]['context']['asset'] == current_asset:
                context_representations_by_id[k] = linked_representations_by_id.pop(k)

        placeholders = map(placeholder_class, self.get_template_nodes())
        placeholders = filter(lambda ph : ph.is_valid, placeholders)
        placeholders = sorted(placeholders, key=lambda ph : ph.order)

        for placeholder in placeholders:
            if placeholder.data['builder_type'] == 'context_asset':
                representations_by_id = context_representations_by_id
            else:
                representations_by_id = linked_representations_by_id
            for representation_id, representation in representations_by_id.items():
                if not placeholder.is_repres_valid(representation):
                    continue
                container = avalon.api.load(
                    loaders_by_name[placeholder.loader],
                    representation_id)
                placeholder.parent(container)
            placeholder.clean()

    def import_template(self, template_path):
        """
        Import template in dcc

        Args:
            template_path (str): fullpath to current task and dcc's template
                file
        """
        raise NotImplementedError

    def get_template_nodes(self):
        """
        Property returning template path. forbidding user to set.
        Getting template path from open pype settings
        bassing on current avalon session
        and solving the path variables if needed.

        Returns:
            str: Solved template path
        """
        raise NotImplementedError
class AbstractPlaceholder:

    attributes = {'builder_type', 'family', 'representation', 'order', 'loader'}
    optional_attributes = {}

    def __init__(self, node):
        self.get_data(node)

    def get_data(self, node):
        raise NotImplementedError

    @property
    def order(self):
        return self.data.get('order')

    @property
    def loader(self):
        return self.data.get('loader')

    @property
    def is_context(self):
        return self.data.get('builder_type') == 'context_asset'

    @property
    def is_valid(self):
        return set(self.attributes).issubset(self.data.keys())

    def parent(self, containers):
        raise NotImplementedError

    def clean(self):
        raise NotImplementedError

    def is_repres_valid(self, representation):
        representation_context = representation['context']

        is_valid = bool(re.match(
            self.data.get('asset', ''), representation_context['asset']))
        is_valid &= bool(re.match(
            self.data.get('hierarchy', ''), representation_context['hierarchy']))
        is_valid &= self.data['representation'] == representation_context['representation']
        is_valid &= self.data['family'] == representation_context['family']

        return is_valid
