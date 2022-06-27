import boto3
import logging
import pymssql
from cfn_resource_provider import ResourceProvider

from sqlserver_resource_providers import connection_info
from sqlserver_resource_providers.connection_info import _get_password_from_dict

log = logging.getLogger()

request_schema = {
    "$schema": "http://json-schema.org/draft-04/schema#",
    "type": "object",
    "oneOf": [
        {"required": ["Server", "LoginName", "Password"]},
        {"required": ["Server", "LoginName", "PasswordParameterName"]},
    ],
    "properties": {
        "Server": connection_info.request_schema,
        "LoginName": {
            "type": "string",
            "pattern": r"^[^\[\]]*$",
            "description": "the login name in to create",
        },
        "Password": {"type": "string", "description": "the password for the login"},
        "PasswordParameterName": {
            "type": "string",
            "minLength": 1,
            "description": "the name of the password in the Parameter Store.",
        },
        "DeletionPolicy": {
            "type": "string",
            "default": "Retain",
            "enum": ["Drop", "Retain"],
        },
    },
}


class SQLServerResource(ResourceProvider):
    def __init__(self):
        super(SQLServerResource, self).__init__()
        self.ssm = boto3.client("ssm")
        self.connection = None
        self.connection_info = {}

    def convert_property_types(self):
        self.heuristic_convert_property_types(self.properties)
        self.connection_info = connection_info.from_url(
            self.server_url, self.server_password
        )

    @property
    def deletion_policy(self):
        return self.get("DeletionPolicy")

    @property
    def server_url(self):
        return self.get("Server", {}).get("URL", "")

    @property
    def old_server_url(self):
        return self.get_old("Server", {}).get("URL", self.server_url)

    @property
    def server_password(self) -> str:
        return _get_password_from_dict(self.get("Server"), self.ssm)

    def connect(self, autocommit: bool = False):
        try:
            self.connection = pymssql.connect(**self.connection_info)
            self.connection.autocommit(autocommit)
        except Exception as e:
            raise ValueError("Failed to connect, %s" % e)

    def close(self):
        if not self.connection:
            return

        if self.status == "SUCCESS":
            self.connection.commit()
        else:
            self.connection.rollback()

        self.connection.close()
        self.connection = None

    @staticmethod
    def safe(s):
        return s.replace("'", "''")
