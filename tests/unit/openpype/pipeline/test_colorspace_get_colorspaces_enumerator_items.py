import unittest

from openpype.pipeline.colorspace import get_colorspaces_enumerator_items


class TestGetColorspacesEnumeratorItems(unittest.TestCase):
    def setUp(self):
        self.config_items = {
            "colorspaces": {
                "sRGB": {
                    "aliases": ["sRGB_1"],
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

    def test_colorspaces(self):
        result = get_colorspaces_enumerator_items(self.config_items)
        expected = [
            ("colorspaces::Rec.709", "[colorspace] Rec.709"),
            ("colorspaces::sRGB", "[colorspace] sRGB"),
        ]
        self.assertEqual(result, expected)

    def test_aliases(self):
        result = get_colorspaces_enumerator_items(
            self.config_items, include_aliases=True)
        expected = [
            ("colorspaces::Rec.709", "[colorspace] Rec.709"),
            ("colorspaces::sRGB", "[colorspace] sRGB"),
            ("aliases::rec709_1", "[alias] rec709_1 (Rec.709)"),
            ("aliases::rec709_2", "[alias] rec709_2 (Rec.709)"),
            ("aliases::sRGB_1", "[alias] sRGB_1 (sRGB)"),
        ]
        self.assertEqual(result, expected)

    def test_looks(self):
        result = get_colorspaces_enumerator_items(
            self.config_items, include_looks=True)
        expected = [
            ("colorspaces::Rec.709", "[colorspace] Rec.709"),
            ("colorspaces::sRGB", "[colorspace] sRGB"),
            ("looks::sRGB_to_Rec.709", "[look] sRGB_to_Rec.709 (sRGB)"),
        ]
        self.assertEqual(result, expected)

    def test_display_views(self):
        result = get_colorspaces_enumerator_items(
            self.config_items, include_display_views=True)
        expected = [
            ("colorspaces::Rec.709", "[colorspace] Rec.709"),
            ("colorspaces::sRGB", "[colorspace] sRGB"),
            ("displays_views::Rec.709 (ACES)", "[view (display)] Rec.709 (ACES)"),  # noqa: E501
            ("displays_views::sRGB (ACES)", "[view (display)] sRGB (ACES)"),

        ]
        self.assertEqual(result, expected)

    def test_roles(self):
        result = get_colorspaces_enumerator_items(
            self.config_items, include_roles=True)
        expected = [
            ("roles::compositing_linear", "[role] compositing_linear (linear)"),  # noqa: E501
            ("colorspaces::Rec.709", "[colorspace] Rec.709"),
            ("colorspaces::sRGB", "[colorspace] sRGB"),
        ]
        self.assertEqual(result, expected)

    def test_all(self):
        message_config_keys = ", ".join(
            "'{}':{}".format(
                key,
                set(self.config_items.get(key, {}).keys())
            ) for key in self.config_items.keys()
        )
        print("Testing with config: [{}]".format(message_config_keys))
        result = get_colorspaces_enumerator_items(
            self.config_items,
            include_aliases=True,
            include_looks=True,
            include_roles=True,
            include_display_views=True,
        )
        expected = [
            ("roles::compositing_linear", "[role] compositing_linear (linear)"),  # noqa: E501
            ("colorspaces::Rec.709", "[colorspace] Rec.709"),
            ("colorspaces::sRGB", "[colorspace] sRGB"),
            ("aliases::rec709_1", "[alias] rec709_1 (Rec.709)"),
            ("aliases::rec709_2", "[alias] rec709_2 (Rec.709)"),
            ("aliases::sRGB_1", "[alias] sRGB_1 (sRGB)"),
            ("looks::sRGB_to_Rec.709", "[look] sRGB_to_Rec.709 (sRGB)"),
            ("displays_views::Rec.709 (ACES)", "[view (display)] Rec.709 (ACES)"),  # noqa: E501
            ("displays_views::sRGB (ACES)", "[view (display)] sRGB (ACES)"),
        ]
        self.assertEqual(result, expected)


if __name__ == "__main__":
    unittest.main()
