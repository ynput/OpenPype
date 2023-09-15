import pyblish.api

from openpype.lib import EnumDef
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
        self.log.debug(f"Found tycache attributes: {tycache_boolean_attributes}")

    @classmethod
    def get_attribute_defs(cls):
        tyc_attr_enum = ["tycacheChanAge", "tycacheChanGroups", "tycacheChanPos",
                         "tycacheChanRot", "tycacheChanScale", "tycacheChanVel",
                         "tycacheChanSpin", "tycacheChanShape", "tycacheChanMatID",
                         "tycacheChanMapping", "tycacheChanMaterials",
                         "tycacheChanCustomFloat"
                         ]

        return [
            EnumDef("all_tyc_attrs",
                    tyc_attr_enum,
                    default=None,
                    multiselection=True

            )
        ]
"""

  .tycacheChanCustomFloat : boolean
  .tycacheChanCustomVector : boolean
  .tycacheChanCustomTM : boolean
  .tycacheChanPhysX : boolean
  .tycacheMeshBackup : boolean
  .tycacheCreateObject : boolean
  .tycacheCreateObjectIfNotCreated : boolean
  .tycacheLayer : string
  .tycacheObjectName : string
  .tycacheAdditionalCloth : boolean
  .tycacheAdditionalSkin : boolean
  .tycacheAdditionalSkinID : boolean
  .tycacheAdditionalSkinIDValue : integer
  .tycacheAdditionalTerrain : boolean
  .tycacheAdditionalVDB : boolean
  .tycacheAdditionalSplinePaths : boolean
  .tycacheAdditionalTyMesher : boolean
  .tycacheAdditionalGeo : boolean
  .tycacheAdditionalObjectList_deprecated : node array
  .tycacheAdditionalObjectList : maxObject array
  .tycacheAdditionalGeoActivateModifiers : boolean
  .tycacheSplines: boolean
  .tycacheSplinesAdditionalSplines : boolean
  .tycacheSplinesAdditionalSplinesObjectList_deprecated : node array
  .tycacheSplinesAdditionalObjectList : maxObject array

"""
