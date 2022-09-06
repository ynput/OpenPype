import os.path
import toml
import abc
import six
from packaging import version

file_url = "C:/Users/petrk/PycharmProjects/Pype3.0/pype/pyproject.toml"


@six.add_metaclass(abc.ABCMeta)
class AbstractTomlProvider:

    @abc.abstractmethod
    def get_toml(self):
        """
            Returns dict containing toml information


            Returns:
                (dict)
        """
        pass


class FileTomlProvider(AbstractTomlProvider):

    def __init__(self, source_url):
        self.source_url = source_url

    def get_toml(self):
        if not os.path.exists(self.source_url):
            raise ValueError(f"{self.source_url} doesn't exist. "
                             "Provide path to real toml.")

        with open(self.source_url) as fp:
            return toml.load(fp)


def is_valid_toml(toml):
    """Validates that 'toml' contains all required fields.

    Args:
        toml (dict)
    Returns:
        True if all required keys present
    Raises:
        KeyError
    """
    required_fields = ["tool.poetry"]

    for field in required_fields:
        fields = field.split('.')
        value = toml
        while fields:
            key = fields.pop(0)
            value = value.get(key)

            if not value:
                raise KeyError(f"Toml content must contain {field}")

    return True


def merge_tomls(main_toml, addon_toml):
    """Add dependencies from 'addon_toml' to 'main_toml'.

    Looks for mininimal compatible version from both tomls.

    Returns:
        (dict): updated 'main_toml' with additional/updated dependencies
    """
    dependency_keyes = ["dependencies", "dev-dependencies"]
    for key in dependency_keyes:
        main_poetry = main_toml["tool"]["poetry"][key]
        addon_poetry = addon_toml["tool"]["poetry"][key]
        for dependency, dep_version in addon_poetry.items():
            if main_poetry.get(dependency):
                main_version = main_poetry[dependency]
                # max ==  smaller from both versions
                dep_version = max(version.parse(dep_version),
                                  version.parse(main_version))

            main_poetry[dependency] = str(dep_version)

        main_toml["tool"]["poetry"][key] = main_poetry

    return main_toml


if __name__ == "__main__":
    provider = FileTomlProvider(file_url)
    toml = provider.get_toml()
    print(toml)

    is_valid_toml(toml)
