
from openpype.hosts.harmony.api.lib import _ZipFile
from pathlib import Path

def test_zip():
    source = "c:/Users/petrk/Downloads/fbb_fbb100_sh0020_workfileAnimation_v010.zip"
    dest = "c:/projects/temp/unzipped_with_python_111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111111\\2222222222222222222222222222222222222222222222222222222222222222222222222222222222"

    dest = Path(dest)
    with _ZipFile(source, "r") as zip_ref:
        zip_ref.extractall(dest.as_posix())