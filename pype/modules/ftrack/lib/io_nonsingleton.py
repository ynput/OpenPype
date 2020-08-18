"""
Wrapper around interactions with the database

Copy of io module in avalon-core.
 - In this case not working as singleton with api.Session!
"""
from avalon.api import AvalonMongoConnection

DbConnector = AvalonMongoConnection
