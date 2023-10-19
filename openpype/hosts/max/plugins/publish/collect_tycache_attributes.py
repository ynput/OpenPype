import pyblish.api

from openpype.lib import EnumDef, TextDef
from openpype.pipeline.publish import OpenPypePyblishPluginMixin


class CollectTyCacheData(pyblish.api.InstancePlugin,
                         OpenPypePyblishPluginMixin):
    """Collect Channel Attributes for TyCache Export"""

    order = pyblish.api.CollectorOrder + 0.02
    label = "Collect tyCache attribute Data"
    hosts = ['max']
    families = ["tycache"]

    def process(self, instance):
        attr_values = self.get_attr_values_from_data(instance.data)
        attributes = {}
        for attr_key in attr_values.get("tycacheAttributes", []):
            attributes[attr_key] = True

        for key in ["tycacheLayer", "tycacheObjectName"]:
            attributes[key] = attr_values.get(key, "")

        # Collect the selected channel data before exporting
        instance.data["tyc_attrs"] = attributes
        self.log.debug(
            f"Found tycache attributes: {attributes}"
        )

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
                         "tycacheCreateObject",
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
        tyc_default_attrs = ["tycacheChanGroups", "tycacheChanPos",
                             "tycacheChanRot", "tycacheChanScale",
                             "tycacheChanVel", "tycacheChanShape",
                             "tycacheChanMatID", "tycacheChanMapping",
                             "tycacheChanMaterials",
                             "tycacheCreateObjectIfNotCreated"]
        return [
            EnumDef("tycacheAttributes",
                    tyc_attr_enum,
                    default=tyc_default_attrs,
                    multiselection=True,
                    label="TyCache Attributes"),
            TextDef("tycacheLayer",
                    label="TyCache Layer",
                    tooltip="Name of tycache layer",
                    default="$(tyFlowLayer)"),
            TextDef("tycacheObjectName",
                    label="TyCache Object Name",
                    tooltip="TyCache Object Name",
                    default="$(tyFlowName)_tyCache")
        ]
