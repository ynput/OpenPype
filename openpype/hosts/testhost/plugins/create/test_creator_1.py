from openpype import resources
from openpype.hosts.testhost import api
from openpype.pipeline import (
    Creator,
    CreatedInstance,
    lib
)


class TestCreatorOne(Creator):
    family = "test_one"
    description = "Testing creator of testhost"

    def get_icon(self):
        return resources.get_openpype_splash_filepath()

    def create(self, subset_name, data, options=None):
        avalon_instance = CreatedInstance(self.family, subset_name, data, self)
        api.pipeline.HostContext.add_instance(avalon_instance.data_to_store())
        self.log.info(avalon_instance.data)
        return avalon_instance

    def get_default_variants(self):
        return [
            "myVariant",
            "variantTwo",
            "different_variant"
        ]

    def get_attribute_defs(self):
        output = [
            lib.NumberDef("number_key", label="Number")
        ]
        return output

    def get_detail_description(self):
        return """# Relictus funes est Nyseides currusque nunc oblita

## Causa sed

Lorem markdownum posito consumptis, *plebe Amorque*, abstitimus rogatus fictaque
gladium Circe, nos? Bos aeternum quae. Utque me, si aliquem cladis, et vestigia
arbor, sic mea ferre lacrimae agantur prospiciens hactenus. Amanti dentes pete,
vos quid laudemque rastrorumque terras in gratantibus **radix** erat cedemus?

Pudor tu ponderibus verbaque illa; ire ergo iam Venus patris certe longae
cruentum lecta, et quaeque. Sit doce nox. Anteit ad tempora magni plenaque et
videres mersit sibique auctor in tendunt mittit cunctos ventisque gravitate
volucris quemquam Aeneaden. Pectore Mensis somnus; pectora
[ferunt](http://www.mox.org/oculosbracchia)? Fertilitatis bella dulce et suum?
        """
