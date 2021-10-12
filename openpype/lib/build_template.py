from openpype.plugins.load.abstract_load_template import TemplateLoader as maya_TemplateLoader

def get_concrete_template_loader(context):
    if context['DCC'] == 'Maya':
        return maya_TemplateLoader
    raise ValueError('DCC not found for template')

class BuildWorkfileTemplate:
    #log = logging.getLogger("BuildWorkfile")

    def process(self):
        containers = self.build_workfile()

        return containers

    def build_workfile(self):
        concrete = get_concrete_template_loader({'DCC':'Maya'})
        instance = concrete()

        # Get current asset name and entity
        # current_asset_name = avalon.io.Session["AVALON_ASSET"]
        # current_asset_entity = avalon.io.find_one({
        #     "type": "asset",
        #     "name": current_asset_name
        # })

        # # Skip if asset was not found
        # if not current_asset_entity:
        #     print("Asset entity with name `{}` was not found".format(
        #         current_asset_name
        #     ))
        #     return
        # current_task = current_asset_entity['task']
        # ConcreteLoader = get_concrete_template_loader({'DCC':'Maya'})
        # template_loader = ConcreteLoader(current_task)

        # context_assets, linked_assets = template_loader.load_template()

        # #Prepare available loaders
        # loaders_by_name = {}
        # for loader in avalon.api.discover(avalon.api.Loader):
        #     loader_name = loader.__name__
        #     if loader_name in loaders_by_name:
        #         raise KeyError(
        #             "Duplicated loader name {0}!".format(loader_name)
        #         )
        #     loaders_by_name[loader_name] = loader

        # # Skip if there are any loaders
        # if not loaders_by_name:
        #     self.log.warning("There are no registered loaders.")
        #     return



        # # Get current task name
        # current_task_name = avalon.io.Session["AVALON_TASK"]

        # # Prepare assets to process by workfile presets
        # assets = []
        # current_asset_id = None
        # if current_context_profiles:
        #     # Add current asset entity if preset has current context set
        #     assets.append(current_asset_entity)
        #     current_asset_id = current_asset_entity["_id"]

        # if link_context_profiles:
        #     # Find and append linked assets if preset has set linked mapping
        #     link_assets = get_linked_assets(current_asset_entity)
        #     if link_assets:
        #         assets.extend(link_assets)


        # # Prepare entities from database for assets
        # prepared_entities = self._collect_last_version_repres(assets)

        # # Load containers by prepared entities and presets
        # loaded_containers = []
        # # - Current asset containers
        # if current_asset_id and current_asset_id in prepared_entities:
        #     current_context_data = prepared_entities.pop(current_asset_id)
        #     loaded_data = self.load_containers_by_asset_data(
        #         current_context_data, current_context_profiles, loaders_by_name
        #     )
        #     if loaded_data:
        #         loaded_containers.append(loaded_data)

        # # - Linked assets container
        # for linked_asset_data in prepared_entities.values():
        #     loaded_data = self.load_containers_by_asset_data(
        #         linked_asset_data, link_context_profiles, loaders_by_name
        #     )
        #     if loaded_data:
        #         loaded_containers.append(loaded_data)

        # # Return list of loaded containers
        # return loaded_containers
