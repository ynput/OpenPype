from openpype.hosts.testhost import api
from openpype.pipeline import (
    Creator,
    CreatedInstance,
    lib
)


class TestCreatorTwo(Creator):
    family = "test_two"

    def create(self, subset_name, data, options=None):
        avalon_instance = CreatedInstance(self.family, subset_name, data, self)
        api.pipeline.HostContext.add_instance(avalon_instance.data_to_store())
        self.log.info(avalon_instance.data)
        return avalon_instance

    def get_attribute_defs(self):
        output = [
            lib.NumberDef("number_key"),
            lib.TextDef("text_key")
        ]
        return output
