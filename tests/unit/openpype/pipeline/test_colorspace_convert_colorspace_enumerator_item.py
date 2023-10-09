import unittest
from openpype.pipeline.colorspace import convert_colorspace_enumerator_item


class TestConvertColorspaceEnumeratorItem(unittest.TestCase):
    def setUp(self):
        self.config_items = {
            "colorspaces": {
                "sRGB": {
                    "aliases": ["sRGB_1"],
                    "family": "colorspace",
                    "categories": ["colors"],
                    "equalitygroup": "equalitygroup",
                },
                "Rec.709": {
                    "aliases": ["rec709_1", "rec709_2"],
                },
            },
            "looks": {
                "sRGB_to_Rec.709": {
                    "process_space": "sRGB",
                },
            },
            "displays_views": {
                "sRGB (ACES)": {
                    "view": "sRGB",
                    "display": "ACES",
                },
                "Rec.709 (ACES)": {
                    "view": "Rec.709",
                    "display": "ACES",
                },
            },
            "roles": {
                "compositing_linear": {
                    "colorspace": "linear",
                },
            },
        }

    def test_valid_item(self):
        colorspace_item_data = convert_colorspace_enumerator_item(
            "colorspaces::sRGB", self.config_items)
        self.assertEqual(
            colorspace_item_data,
            {
                "name": "sRGB",
                "type": "colorspaces",
                "aliases": ["sRGB_1"],
                "family": "colorspace",
                "categories": ["colors"],
                "equalitygroup": "equalitygroup"
            }
        )

        alias_item_data = convert_colorspace_enumerator_item(
            "aliases::rec709_1", self.config_items)
        self.assertEqual(
            alias_item_data,
            {
                "aliases": ["rec709_1", "rec709_2"],
                "name": "Rec.709",
                "type": "colorspace"
            }
        )

        display_view_item_data = convert_colorspace_enumerator_item(
            "displays_views::sRGB (ACES)", self.config_items)
        self.assertEqual(
            display_view_item_data,
            {
                "type": "displays_views",
                "name": "sRGB (ACES)",
                "view": "sRGB",
                "display": "ACES"
            }
        )

        role_item_data = convert_colorspace_enumerator_item(
            "roles::compositing_linear", self.config_items)
        self.assertEqual(
            role_item_data,
            {
                "name": "compositing_linear",
                "type": "roles",
                "colorspace": "linear"
            }
        )

        look_item_data = convert_colorspace_enumerator_item(
            "looks::sRGB_to_Rec.709", self.config_items)
        self.assertEqual(
            look_item_data,
            {
                "type": "looks",
                "name": "sRGB_to_Rec.709",
                "process_space": "sRGB"
            }
        )

    def test_invalid_item(self):
        config_items = {
            "RGB": {
                "sRGB": {"red": 255, "green": 255, "blue": 255},
                "AdobeRGB": {"red": 255, "green": 255, "blue": 255},
            }
        }
        with self.assertRaises(KeyError):
            convert_colorspace_enumerator_item("RGB::invalid", config_items)

    def test_missing_config_data(self):
        config_items = {}
        with self.assertRaises(KeyError):
            convert_colorspace_enumerator_item("RGB::sRGB", config_items)


if __name__ == '__main__':
    unittest.main()
