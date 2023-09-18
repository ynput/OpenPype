import pyblish.api

from openpype.lib import EnumDef, TextDef
from openpype.pipeline.publish import OpenPypePyblishPluginMixin


class CollectTyCacheData(pyblish.api.InstancePlugin,
                         OpenPypePyblishPluginMixin):
    """Collect Review Data for Preview Animation"""

    order = pyblish.api.CollectorOrder + 0.02
    label = "Collect tyCache attribute Data"
    hosts = ['max']
    families = ["tycache"]

    def process(self, instance):
        all_tyc_attributes_dict = {}
        attr_values = self.get_attr_values_from_data(instance.data)
        tycache_boolean_attributes = attr_values.get("all_tyc_attrs")
        if tycache_boolean_attributes:
            for attrs in tycache_boolean_attributes:
                all_tyc_attributes_dict[attrs] = True
        tyc_layer_attr = attr_values.get("tycache_layer")
        if tyc_layer_attr:
            all_tyc_attributes_dict["tycacheLayer"] = (
                tyc_layer_attr)
        tyc_objname_attr = attr_values.get("tycache_objname")
        if tyc_objname_attr:
            all_tyc_attributes_dict["tycache_objname"] = (
                tyc_objname_attr)
        self.log.debug(
            f"Found tycache attributes: {all_tyc_attributes_dict}")

    @classmethod
    def get_attribute_defs(cls):
        # TODO: Support the attributes with maxObject array
        tyc_attr_enum = ["tycacheChanAge", "tycacheChanGroups",
                         "tycacheChanPos", "tycacheChanRot",
                         "tycacheChanScale", "tycacheChanVel",
                         "tycacheChanSpin", "tycacheChanShape",
                         "tycacheChanMatID", "tycacheChanMapping",
                         "tycacheChanMaterials", "tycacheChanCustomFloat"
                         "tycacheChanCustomVector", "tycacheChanCustomTM",
                         "tycacheChanPhysX", "tycacheMeshBackup",
                         "tycacheCreateObjectIfNotCreated",
                         "tycacheAdditionalCloth",
                         "tycacheAdditionalSkin",
                         "tycacheAdditionalSkinID",
                         "tycacheAdditionalSkinIDValue",
                         "tycacheAdditionalTerrain",
                         "tycacheAdditionalVDB",
                         "tycacheAdditionalSplinePaths",
                         "tycacheAdditionalGeo",
                         "tycacheAdditionalGeoActivateModifiers",
                         "tycacheSplines",
                         "tycacheSplinesAdditionalSplines"
                         ]

        return [
            EnumDef("all_tyc_attrs",
                    tyc_attr_enum,
                    default=None,
                    multiselection=True,
                    label="TyCache Attributes"),
            TextDef("tycache_layer",
                    label="TyCache Layer",
                    tooltip="Name of tycache layer",
                    default=""),
            TextDef("tycache_objname",
                    label="TyCache Object Name",
                    tooltip="TyCache Object Name",
                    default="")
        ]
