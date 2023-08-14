import os
import yaml
from pprint import pprint
from typing import Any


file_path = 'D:/jt_dev/hpipe/newdev/OpenPype/openpype/hpipe/studio_config.yaml'

class ConfigReader:
    def __init__(self):
        yaml_file_path = file_path #os.path.join(os.path.dirname(os.path.__file__),'studio_config.yaml')
        with open(yaml_file_path, 'r') as file:
            yaml_content = file.read()
        self.config = yaml.load(yaml_content, Loader=yaml.FullLoader)
        self.set_properties()

    def set_properties(self):
        for key, value in self.config.items():
            setattr(self, key, value)

    def __getattr__(self, key: str) -> Any:
            if key in self.config:
                return self.config[key]
            raise AttributeError(f"'ConfigReader' object has no attribute '{key}'")

if __name__ == "__main__":
    config = ConfigReader()
    print(dir(config))
