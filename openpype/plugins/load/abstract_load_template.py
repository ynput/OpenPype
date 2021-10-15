import avalon
from openpype.settings import get_project_settings
import collections
from openpype.lib import get_linked_assets

#### Copy from BuildWorkfile in avalon_context.py
#### TODO : Move those function into a lib
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

    @property
    def template_path(self):
        project_settings = get_project_settings(avalon.io.Session["AVALON_PROJECT"])
        for profile in project_settings['maya']['workfile_build']['profiles']: #get DCC
            if 'Modeling' in profile['task_types']: # Get tasktype
                return profile['path'] #Validate path
        raise ValueError("No matching profile found for task '{}' in DCC '{}'".format('Modeling', 'maya'))

    def __init__(self):

        self.import_template(self.template_path)

        loaders_by_name = get_loader_by_name()
        # Skip if there are any loaders
        if not loaders_by_name:
            self.log.warning("There are no registered loaders.")
            return

        #get_assets
        current_asset_entity = avalon.io.find_one({
            "type": "asset",
            "name": avalon.io.Session["AVALON_ASSET"]
        })

        current_entities = _collect_last_version_repres([current_asset_entity])
        assets = get_linked_assets(current_asset_entity)
        linked_entities = _collect_last_version_repres(assets)

        placeholders = (
            self.placeholderize(node) for node
            in self.get_template_nodes()
            if self.is_valid_placeholder(node)
        )
        sorted_placeholders = sorted(placeholders, key=lambda x: x['order'])

        for ph in sorted_placeholders:
            if ph['context_asset']:
                repres = self.get_representations_by_placeholder(ph, current_entities)
            else:
                repres = self.get_representations_by_placeholder(ph, linked_entities)
            for rep in repres:
                container = avalon.api.load(
                        loaders_by_name["ReferenceLoader"],
                        rep
                    )
                self.switch(container, ph['node'])

    def get_representations_by_placeholder(self, ph, entities):
        def validate_representation(representation):
            return (
                ph['family'] == representation['context']['family']
                and ph['representation_type'] == representation['context']['representation']
                and ph['subset'] == representation['context']['subset']
                )

        repres = [subset['version']['repres'] for entity in entities.values() for subset in entity['subsets'].values()]
        repres = [r['_id'] for rep in repres for r in rep if validate_representation(r)] #flatten list + validate

        if len(repres) <1:
            raise ValueError("No representation found for asset {} with:\n"
                  "family : {}\n"
                  "rerpresentation : {}\n"
                  "subset : {}\n".format(ph['name'], ph['family'], ph['representation_type'], ph['subset']))
        return repres

    def placeholderize(self, node):
        return {
            'context_asset': self.get_is_context_asset(node),
            'loader': self.get_loader(node),
            'representation_type': self.get_representation_type(node),
            'family': self.get_family(node),
            'subset': self.get_subset(node),
            'node': node,
            'name': self.get_name(node),
            'order': self.get_order(node),
        }

    def import_template(self, template_path):
        """
        Import template in dcc

        Args:
            template_path (str): fullpath to current task and dcc's template file
        """
        raise NotImplementedError

    def switch(self, container, node):
        raise NotImplementedError

    def get_template_nodes(self):
        raise NotImplementedError

    @staticmethod
    def get_is_context_asset(node):
        raise NotImplementedError

    @staticmethod
    def get_loader(node):
        raise NotImplementedError

    @staticmethod
    def get_type(node):
        raise NotImplementedError

    @staticmethod
    def get_family(node):
        raise NotImplementedError

    @staticmethod
    def get_subset(node):
        raise NotImplementedError

    @staticmethod
    def get_name(node):
        raise NotImplementedError

    @staticmethod
    def get_order(node):
        raise NotImplementedError
