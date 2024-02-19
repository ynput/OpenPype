import re
from enum import Enum


class PathsParts(Enum):
    WINDOWS_L = "L:/2023"
    WINDOWS_PROD9 = "//prod9.prs.vfx.int/fs209/Projets/2023"
    LINUX = "/prod/project"


def extract_version(filepath):
    version_regex = r'[^a-zA-Z\d](v\d{3})[^a-zA-Z\d]'
    results = re.search(version_regex, filepath)
    return results.groups()[-1]
