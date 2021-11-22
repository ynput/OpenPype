import os
import re
import avalon
from abc import ABCMeta, abstractmethod

import six

from openpype.settings import get_project_settings
from openpype.lib import Anatomy, get_linked_assets, get_loaders_by_name,\
    collect_last_version_repres


@six.add_metaclass(ABCMeta)
class AbstractTemplateLoader:
    """
    Abstraction of Template Loader.

    Properties:
        template_path : property to get current template path

    Methods:
        import_template : Abstract Method. Used to load template,
            depending on current dcc
        get_template_nodes : Abstract Method. Used to query nodes acting
            as placeholders. Depending on current dcc
    """

    def __init__(self, placeholder_class):

        self.loaders_by_name = get_loaders_by_name()
        self.current_asset = avalon.io.Session["AVALON_ASSET"]
        self.placeholder_class = placeholder_class

        # Skip if there is no loader
        if not self.loaders_by_name:
            self.log.warning("There are no registered loaders.")
            return

    def process(self):
        self.import_template(self.template_path)
        self.populate_template()

    @property
    def template_path(self):
        """
        Property returning template path. Avoiding setter.
        Getting template path from open pype settings based on current avalon
        session and solving the path variables if needed.

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
        build_info = project_settings[current_dcc]['templated_workfile_build']
        profiles = build_info['profiles']

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
                "Template found in openPype settings for task '{}' with DCC "
                "'{}' does not exists. (Not found : {})".format(
                    current_task, current_dcc, solved_path))
        return solved_path

    def populate_template(self):
        """
        Use template placeholders to load assets and parent them in hierarchy

        Arguments :
            current_asset (str):
            loader_by_name (dict(name:loader)):
            placeholder_class (AbstractPlaceHolder):

        Returns:
            None
        """
        placeholder_class = self.placeholder_class
        loaders_by_name = self.loaders_by_name
        current_asset = self.current_asset
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

    @abstractmethod
    def import_template(self, template_path):
        """
        Import template in current dcc

        Args:
            template_path (str): fullpath to current task and
                dcc's template file

        Return:
            None
        """
        pass

    @abstractmethod
    def get_template_nodes(self):
        """
        Returning a list of nodes acting as DCC placeholders for
        templating. The data representation is by user.
        AbstractLoadTemplate (and LoadTemplate) won't directly manipulate nodes

        Args :
            None

        Returns:
            list(AnyNode): Solved template path
        """
        pass


@six.add_metaclass(ABCMeta)
class AbstractPlaceholder:
    """Abstraction of placeholders logic

    Properties:
        attributes: A list of mandatory attribute to decribe placeholder
            and assets to load.
        optional_attributes: A list of optional attribute to decribe
            placeholder and assets to load
        loader: Name of linked loader to use while loading assets
        is_context: Is placeholder linked
            to context asset (or to linked assets)

    Methods:
        is_repres_valid:
        loader:
        order:
        is_valid:
        get_data:
        parent_in_hierachy:

    """

    attributes = {'builder_type', 'family',
                  'representation', 'order', 'loader'}
    optional_attributes = {}

    def __init__(self, node):
        self.get_data(node)

    @abstractmethod
    def get_data(self, node):
        """
        Collect placeholders information.

        Args:
            node (AnyNode): A unique node decided by Placeholder implementation
        """
        raise NotImplementedError

    def order(self):
        """Get placeholder order to sort them by priority
        Priority is lowset first, highest last
        (ex:
            1: First to load
            100: Last to load)

        Returns:
            Int: Order priority
        """
        return self.data.get('order')

    @property
    def loader(self):
        """Return placeholder loader type

        Returns:
            string: Loader name
        """
        return self.data.get('loader')

    @property
    def is_context(self):
        """Return placeholder type
        context_asset: For loading current asset
        linked_asset: For loading linked assets

        Returns:
            bool: true if placeholder is a context placeholder
        """
        return self.data.get('builder_type') == 'context_asset'

    def is_valid(self):
        """Test validity of placeholder
        i.e.: every attributes exists in placeholder data

        Returns:
            Bool: True if every attributes are a key of data
        """
        return set(self.attributes).issubset(self.data.keys())

    @abstractmethod
    def parent_in_hierarchy(self, containers):
        """Place container in correct hierarchy
        given by placeholder

        Args:
            containers (String): Container name returned back by
                placeholder's loader.
        """
        raise NotImplementedError

    @abstractmethod
    def clean(self):
        """Clean placeholder from hierarchy after loading assets.
        """
        raise NotImplementedError

    def is_repres_valid(self, representation):
        """Check that given representation correspond to current
        placeholders values in data

        Args:
            representation (dict): Representations in avalon BDD

        Returns:
            Bool: True if representation correspond to placeholder data
        """
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
