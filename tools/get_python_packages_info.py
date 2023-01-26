# -*- coding: utf-8 -*-
"""Get version and license information on used Python packages.

This is getting over all packages installed with Poetry and printing out
their name, version and available license information from PyPi in Markdown
table format.

Usage:
    ./.poetry/bin/poetry run python ./tools/get_python_packages_info.py

"""

import toml
import requests


packages = []

# define column headers
package_header = "Package"
version_header = "Version"
license_header = "License"

name_col_width = len(package_header)
version_col_width = len(version_header)
license_col_width = len(license_header)

# read lock file to get packages
with open("poetry.lock", "r") as fb:
    lock_content = toml.load(fb)

    for package in lock_content["package"]:
        # query pypi for license information
        url = f"https://pypi.org/pypi/{package['name']}/json"
        response = requests.get(
            f"https://pypi.org/pypi/{package['name']}/json")
        package_data = response.json()
        version = package.get("version") or "N/A"
        try:
            package_license = package_data["info"].get("license") or "N/A"
        except KeyError:
            package_license = "N/A"

        if len(package_license) > 64:
            package_license = f"{package_license[:32]}..."
        packages.append(
            (
                package["name"],
                version,
                package_license
            )
        )

        # update column width based on max string length
        if len(package["name"]) > name_col_width:
            name_col_width = len(package["name"])
        if len(version) > version_col_width:
            version_col_width = len(version)
        if len(package_license) > license_col_width:
            license_col_width = len(package_license)

# pad columns
name_col_width += 2
version_col_width += 2
license_col_width += 2

# print table header
print((f"|{package_header.center(name_col_width)}"
       f"|{version_header.center(version_col_width)}"
       f"|{license_header.center(license_col_width)}|"))

print(
    "|" + ("-" * len(package_header.center(name_col_width))) +
    "|" + ("-" * len(version_header.center(version_col_width))) +
    "|" + ("-" * len(license_header.center(license_col_width))) + "|")

# print rest of the table
for package in packages:
    print((
        f"|{package[0].center(name_col_width)}"
        f"|{package[1].center(version_col_width)}"
        f"|{package[2].center(license_col_width)}|"
    ))
