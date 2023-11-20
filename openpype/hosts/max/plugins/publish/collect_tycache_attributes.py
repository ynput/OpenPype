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
        export_mode = attr_values.get("exportMode")
        instance.data["exportMode"] = 2 if export_mode == "TyCache" else 6
        self.log.debug("{}".format(instance.data["exportMode"]))
        attributes = {}
        for attr_key in attr_values.get("tycacheAttributes", []):
            if export_mode == "TyCache(Splines)" and \
                attr_key not in ["tycacheSplines",
                                 "tycacheSplinesAdditionalSplines",
                                 "tycacheAdditionalSplinePaths",
                                 "tycacheSplinesFilterID"]:
                self.log.warning(
                    f"{attr_key} wont be exported along with {export_mode}")
                continue

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
                         "tycacheAdditionalVDB"
                         "tycacheAdditionalGeo",
                         "tycacheAdditionalGeoActivateModifiers",
                         "tycacheSplines",
                         "tycacheSplinesAdditionalSplines",
                         "tycacheAdditionalSplinePaths",
                         "tycacheSplinesFilterID"
                         ]

        tyc_default_attrs = ["tycacheChanGroups", "tycacheChanPos",
                             "tycacheChanRot", "tycacheChanScale",
                             "tycacheChanVel", "tycacheChanShape",
                             "tycacheChanMatID", "tycacheChanMapping",
                             "tycacheChanMaterials",
                             "tycacheCreateObjectIfNotCreated"]

        tycache_export_mode_enum = ["TyCache", "TyCache(Splines)"]

        return [
            EnumDef("exportMode",
                    tycache_export_mode_enum,
                    default="tycache",
                    label="TyCache Export Mode"),
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
