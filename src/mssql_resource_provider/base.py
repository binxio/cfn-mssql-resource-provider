import logging
from typing import Optional

import boto3
import pymssql
from cfn_resource_provider import ResourceProvider

from mssql_resource_provider import connection_info
from mssql_resource_provider.connection_info import _get_password_from_dict

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


class MSSQLResource(ResourceProvider):
    def __init__(self):
        super(MSSQLResource, self).__init__()
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
            self.connection = pymssql.connect(**self.connection_info, charset="utf8")
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

    def get_database_id(self, name) -> Optional[str]:

        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT schema_id FROM sys.databases 
                    WHERE name = '{MSSQLResource.safe(name)}'
                    """
                )
                rows = cursor.fetchone()
        except pymssql.OperationalError:
            rows = None

        return rows[0] if rows else None

    def get_database_id(self, database: str) -> Optional[str]:
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT database_id FROM master.sys.databases
                    WHERE name = '{MSSQLResource.safe(database)}'
                    """
                )
                rows = cursor.fetchone()
        except pymssql.OperationalError:
            rows = None

        return rows[0] if rows else None

    def get_user_id(self, database: str, username: str) -> Optional[str]:
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT principal_id FROM [{database}].sys.database_principals
                    WHERE name = '{MSSQLResource.safe(username)}'
                    """
                )
                rows = cursor.fetchone()
        except pymssql.OperationalError:
            rows = None

        return rows[0] if rows else None

    @staticmethod
    def get_exception_message(error: pymssql.StandardError) -> str:
        """
        returns a readable message of max 200 characters
        """
        if (
            hasattr(error, "args")
            and isinstance(error.args, tuple)
            and len(error.args) == 2
        ):
            number, msg = error.args
            if isinstance(msg, bytes):
                msg = str(msg, "utf8")
            return f"{number}:{msg}"
        else:
            return str(error)

    def report_failure(self, error: pymssql.StandardError):
        self.fail(self.get_exception_message(error)[0:200])
