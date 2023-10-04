import unittest
from unittest.mock import patch
from openpype.pipeline.colorspace import get_labeled_colorspaces


class TestGetLabeledColorspaces(unittest.TestCase):
    @patch('openpype.pipeline.colorspace.get_ocio_config_colorspaces')
    def test_returns_list_of_tuples(self, mock_get_ocio_config_colorspaces):
        mock_get_ocio_config_colorspaces.return_value = {
            'colorspaces': {
                'sRGB': {},
                'Rec.709': {},
            },
            'looks': {
                'sRGB to Rec.709': {
                    'process_space': 'Rec.709',
                },
            },
            'roles': {
                'reference': {
                    'colorspace': 'sRGB',
                },
            },
        }
        result = get_labeled_colorspaces('config.ocio')
        self.assertIsInstance(result, list)
        self.assertTrue(all(isinstance(item, tuple) for item in result))

    @patch('openpype.pipeline.colorspace.get_ocio_config_colorspaces')
    def test_includes_colorspaces(self, mock_get_ocio_config_colorspaces):
        mock_get_ocio_config_colorspaces.return_value = {
            'colorspaces': {
                'sRGB': {}
            },
            'looks': {},
            'roles': {},
        }
        result = get_labeled_colorspaces('config.ocio', include_aliases=False, include_looks=False, include_roles=False)
        self.assertEqual(result, [('sRGB', '[colorspace] sRGB')])

    @patch('openpype.pipeline.colorspace.get_ocio_config_colorspaces')
    def test_includes_aliases(self, mock_get_ocio_config_colorspaces):
        mock_get_ocio_config_colorspaces.return_value = {
            'colorspaces': {
                'sRGB': {
                    'aliases': ['sRGB (D65)'],
                },
            },
            'looks': {},
            'roles': {},
        }
        result = get_labeled_colorspaces('config.ocio', include_aliases=True, include_looks=False, include_roles=False)
        self.assertEqual(result, [('sRGB', '[colorspace] sRGB'), ('sRGB (D65)', '[alias] sRGB (D65) (sRGB)')])

    @patch('openpype.pipeline.colorspace.get_ocio_config_colorspaces')
    def test_includes_looks(self, mock_get_ocio_config_colorspaces):
        mock_get_ocio_config_colorspaces.return_value = {
            'colorspaces': {},
            'looks': {
                'sRGB to Rec.709': {
                    'process_space': 'Rec.709',
                },
            },
            'roles': {},
        }
        result = get_labeled_colorspaces('config.ocio', include_aliases=False, include_looks=True, include_roles=False)
        self.assertEqual(result, [('sRGB to Rec.709', '[look] sRGB to Rec.709 (Rec.709)')])

    @patch('openpype.pipeline.colorspace.get_ocio_config_colorspaces')
    def test_includes_roles(self, mock_get_ocio_config_colorspaces):
        mock_get_ocio_config_colorspaces.return_value = {
            'colorspaces': {},
            'looks': {},
            'roles': {
                'reference': {
                    'colorspace': 'sRGB',
                },
            },
        }
        result = get_labeled_colorspaces('config.ocio', include_aliases=False, include_looks=False, include_roles=True)
        self.assertEqual(result, [('reference', '[role] reference (sRGB)')])
