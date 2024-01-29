"""
WIP: .\.poetry\bin\poetry.exe run python ./start.py runtests C:\CODE\__PYPE\ayon-openpype\tests\integration\hosts\traypublisher\test_create_csv_ingest.py
"""

import os
import pytest
from unittest.mock import MagicMock, patch
from openpype.hosts.traypublisher.api.plugin import TrayPublishCreator

# Assuming the IngestCSV class is in create_csv_ingest.py as specified
from openpype.hosts.traypublisher.plugins.create import create_csv_ingest

# Constants for tests
VALID_FOLDER = "valid_folder"
VALID_FILENAME = "valid_file.csv"
INVALID_FOLDER = "invalid_folder"
INVALID_FILENAME = "invalid_file.csv"
VALID_SUBSET_NAME = "valid_subset"
VALID_INSTANCE_DATA = {"some": "data"}
VALID_PRE_CREATE_DATA = {
    "csv_filepath_data": {
        "directory": VALID_FOLDER,
        "filenames": [VALID_FILENAME]
    }
}
INVALID_PRE_CREATE_DATA = {
    "csv_filepath_data": {
        "directory": INVALID_FOLDER,
        "filenames": [INVALID_FILENAME]
    }
}

# Mocks for external dependencies
mock_get_asset_by_name = MagicMock()
mock_get_subset_name = MagicMock(return_value="subset_name")
mock_CreatedInstance = MagicMock()

# Patching external dependencies
@pytest.fixture(autouse=True)
def mock_external_dependencies():
    with patch('openpype.hosts.traypublisher.plugins.create.create_csv_ingest.get_asset_by_name', mock_get_asset_by_name), \
         patch('openpype.hosts.traypublisher.plugins.create.create_csv_ingest.get_subset_name', mock_get_subset_name), \
         patch('openpype.hosts.traypublisher.plugins.create.create_csv_ingest.CreatedInstance', mock_CreatedInstance):
        yield

# Parametrized test cases
@pytest.mark.parametrize(
    "subset_name, instance_data, pre_create_data, expected_exception, test_id",
    [
        # Happy path tests
        (VALID_SUBSET_NAME, VALID_INSTANCE_DATA, VALID_PRE_CREATE_DATA, None, "happy_path_valid_data"),

        # Edge cases
        # ... (define edge cases here)

        # Error cases
        (VALID_SUBSET_NAME, VALID_INSTANCE_DATA, INVALID_PRE_CREATE_DATA, FileNotFoundError, "error_invalid_folder"),
        # ... (define other error cases here)
    ]
)
def test_create(subset_name, instance_data, pre_create_data, expected_exception, test_id, mock_external_dependencies):
    # Arrange
    creator = create_csv_ingest.IngestCSV()

    # Act and Assert
    if expected_exception:
        with pytest.raises(expected_exception):
            creator.create(subset_name, instance_data, pre_create_data)
    else:
        creator.create(subset_name, instance_data, pre_create_data)
        # Assert (more assertions can be added here to validate the behavior)
        mock_CreatedInstance.assert_called()
