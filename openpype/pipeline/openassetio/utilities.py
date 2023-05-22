# -*- coding: utf-8 -*-
"""Various tools for openassetio integration inside AYON/OpenPype."""
from abc import ABC, abstractmethod
from urllib.parse import urlparse, parse_qs

from openassetio import constants, TraitsData
from openassetio.managerApi import ManagerInterface

class ManagerBase(ABC, ManagerInterface):
    @property
    @abstractmethod
    def _reference_prefix(self):
        return "ayon://"

    def managementPolicy(
            self, traitSets, Set=None, p_str=None, *args, **kwargs):
        return [TraitsData() for _ in traitSets]

    def info(self):
        return {
            constants.kField_EntityReferencesMatchPrefix: self.__reference_prefix  # noqa: E501
        }

    def isEntityReferenceString(self, someString, hostSession):
        return someString.startswith(self.__reference_prefix)

    @staticmethod
    def parse_reference(reference: str):
        """Parse reference string into dictionary.

        This will take reference string (url) and parse
        it into individual components.

        Example:
            op://projectX/assets/chars/Bob/modelMain?version=1#abc

            will result in

            {
                "project": "projectX",
                "hierarchy": "assets/chars",
                "asset": "Bob",
                "subset": "modelMain",
                "version": 1,
                "representation": "abc"
            }

        Args:
            reference (str): Reference string

        Returns:
            dict: Parsed reference string into dictionary.

        """
        result = urlparse(reference)
        query_string = parse_qs(result.query)
        return {
            "project_name": result.hostname,
            "hierarchy": result.path.split("/")[:-2],
            "asset": result.path.split("/")[-2],
            "subset": result.path.split("/")[-1],
            "version": query_string.get("version", None),
            "representation": result.fragment
        }
