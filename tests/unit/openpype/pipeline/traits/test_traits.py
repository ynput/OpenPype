import openassetio_mediacreation as mc
from openassetio.trait import TraitsData
import json


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
    #data.addTrait(mc.traits.content.LocatableContentTrait.kId)
    assert data.hasTrait(mc.traits.content.LocatableContentTrait.kId)
    _print_data(data)
