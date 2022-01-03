from openpype.lib.abstract_template_loader import AbstractTemplateLoader, AbstractPlaceholder
from avalon import photoshop
import tempfile


class PhotoshopTemplateLoader(AbstractTemplateLoader):
    def import_template(self, template_path):
        print("Looking for ", template_path)
        stub = photoshop.stub()
        stub.open(template_path)
        # Save as temp file
        path = tempfile.NamedTemporaryFile().name
        stub.saveAs(image_path=path, ext='psd', as_copy=False)


    def get_loaded_containers_by_id(self):
        return super().get_loaded_containers_by_id()

    def get_template_nodes(self):
        return []


class PhotoshopPlaceholder(AbstractPlaceholder):
    def parent_in_hierarchy(self, containers):
        return super().parent_in_hierarchy(containers)

    def get_data(self, node):
        return super().get_data(node)

    def clean(self):
        return super().clean()

    def convert_to_db_filters(self, current_asset, linked_asset):
        return super().convert_to_db_filters(current_asset, linked_asset)