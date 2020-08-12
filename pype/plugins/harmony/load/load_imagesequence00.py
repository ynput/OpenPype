import os

import json

file = r"G:\My Drive\pypeRoot\milo_s01\episodes\ml102\ml102_shots\ml102_sh0850\publish\image\imageForComp\v001\ml_ml102_sh0850_imageForComp_v001.json"

with open(file) as json_file:
    data = json.load(json_file)

layers = list()

for child in data['children']:
    if child.get("filename"):
        print(child["filename"])
        layers.append(child["filename"])
    else:
        for layer in child['children']:
            if layer.get("filename"):
                print(layer["filename"])
                layers.append(layer["filename"])

for layer in sorted(layers):
    print(layer)
