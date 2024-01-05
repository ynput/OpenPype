import openassetio_mediacreation as mc
from openassetio.trait import TraitsData
import json
import openpype.pipeline.traits as traits


def _print_data(data):
    as_dict = {
        trait_id: {
            property_key: data.getTraitProperty(trait_id, property_key)
            for property_key in data.traitPropertyKeys(trait_id)
        }
        for trait_id in data.traitSet()
    }
    print(json.dumps(as_dict))


def test_traits_data():
    data = TraitsData()
    lc = mc.traits.content.LocatableContentTrait(data)
    lc.setLocation("https://www.google.com")
    assert data.hasTrait(mc.traits.content.LocatableContentTrait.kId)
    _print_data(data)


def test_generated_traits():
    data = TraitsData()
    import openpype.pipeline.traits.generated as traits
    version_t = traits.openassetio_mediacreation.traits.lifecycle.StableTrait

    version_t.imbueTo(data)
    assert data.hasTrait(traits.openassetio_mediacreation.traits.lifecycle.StableTrait.kId)


def test_get_available_traits_ids(printer):
    trait_ids = traits.get_available_traits_ids()
    assert len(trait_ids) > 0
    assert "ayon:usage.Subset" in trait_ids
    for trait_id in sorted(trait_ids):
        printer(trait_id)
