import os
import re
import avalon
from openpype.settings import get_project_settings
from openpype.lib import Anatomy, get_linked_assets, get_loaders_by_name,\
    collect_last_version_repres


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
            solved_path = None
            while True:
                solved_path = anatomy.path_remapper(path)
                if solved_path == path:
                    break
                path = solved_path
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

        loaders_by_name = get_loaders_by_name()

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
        assets_to_load = {asset['name'] for asset in linked_asset_entities}
        version_repres = collect_last_version_repres(
            [current_asset_entity] + linked_asset_entities)

        representations_by_id = {
            representation['_id']: representation
            for asset in version_repres.values()
            for subset in asset['subsets'].values()
            for representation in subset['version']['repres']}

        context_representations_by_id = dict()
        linked_representations_by_id = dict()
        for k in representations_by_id.keys():
            asset = representations_by_id[k]['context']['asset']
            if asset == current_asset:
                context_representations_by_id[k] = representations_by_id[k]
            else:
                linked_representations_by_id[k] = representations_by_id[k]

        # Def placeholders
        placeholders = map(placeholder_class, self.get_template_nodes())
        valid_placeholders = filter(placeholder_class.is_valid, placeholders)
        sorted_placeholders = sorted(valid_placeholders,
                                     key=placeholder_class.order)

        loaded_assets = set()
        for placeholder in sorted_placeholders:
            if placeholder.data['builder_type'] == 'context_asset':
                representations_by_id = context_representations_by_id
                assets_to_load.add(current_asset)
            else:
                representations_by_id = linked_representations_by_id
            for items in representations_by_id.items():
                representation_id, representation = items
                if not placeholder.is_repres_valid(representation):
                    continue
                container = avalon.api.load(
                    loaders_by_name[placeholder.loader],
                    representation_id)
                placeholder.parent_in_hierarchy(container)
                loaded_assets.add(representation['context']['asset'])
            placeholder.clean()

        if not loaded_assets == assets_to_load:
            unloaded = assets_to_load - loaded_assets
            print("Error found while loading {}".format(unloaded))
            print("It's possible that a needed asset wasn't published")
            print("or that the build template is malformed, "
                  "continue at your own risks.")

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

    attributes = {'builder_type', 'family',
                  'representation', 'order', 'loader'}
    optional_attributes = {}

    def __init__(self, node):
        self.get_data(node)

    def get_data(self, node):
        raise NotImplementedError

    def order(self):
        return self.data.get('order')

    @property
    def loader(self):
        return self.data.get('loader')

    @property
    def is_context(self):
        return self.data.get('builder_type') == 'context_asset'

    def is_valid(self):
        return set(self.attributes).issubset(self.data.keys())

    def parent_in_hierarchy(self, containers):
        raise NotImplementedError

    def clean(self):
        raise NotImplementedError

    def is_repres_valid(self, representation):
        data = self.data

        rep_asset = representation['context']['asset']
        rep_name = representation['context']['representation']
        rep_hierarchy = representation['context']['hierarchy']
        rep_family = representation['context']['family']

        is_valid = bool(re.match(data.get('asset', ''), rep_asset))
        is_valid &= bool(re.match(data.get('hierarchy', ''), rep_hierarchy))
        is_valid &= data['representation'] == rep_name
        is_valid &= data['family'] == rep_family

        return is_valid
