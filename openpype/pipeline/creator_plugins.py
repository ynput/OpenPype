import copy
import collections


class InstanceData(collections.OrderedDict):
    def __init__(self, family, subset_name, data=None):
        self["id"] = "pyblish.avalon.instance"
        self["family"] = family
        self["subset"] = subset_name
        self["active"] = True
        if data:
            self.update(data)


class Creator:
    # Abstract attributes
    label = None
    family = None

    # GUI Purposes
    # - default_variants may not be used if `get_default_variants` is overriden
    default_variants = []

    def __init__(self, headless=False):
        # Creator is running in headless mode (without UI elemets)
        # - we may use UI inside processing this attribute should be checked
        self.headless = headless

    # Process of creation
    # - must expect all data that were passed to init in previous implementation
    def create(self, subset_name, instance_data, options=None):
        instance = PublishInstanceData(
        instance = InstanceData(
            self.family, subset_name, instance_data
        )

    # Just replacement of class attribute `defaults`
    # - gives ability to have some "logic" other than attribute values
    # - by default just return `default_variants` value
    def get_default_variants(self):
        return copy.deepcopy(self.default_variants)

    # Added possibility of returning default variant for default variants
    # - UI purposes
    # - can be different than `get_default_variants` offers
    # - first item from `get_default_variants` should be used if `None`
    #   is returned
    def get_default_variant(self):
        return None

    # Subset name for current Creator plugin
    # - creator may define it's keys for filling
    def get_subset_name(
        self, variant, task_name, asset_id, project_name, host_name=None
    ):
        # Capitalize first letter of user input
        if variant:
            variant = variant[0].capitalize() + variant[1:]

        family = self.family.rsplit(".", 1)[-1]
        return "{}{}".format(family, variant)

    def get_attribute_defs(self):
        return []
